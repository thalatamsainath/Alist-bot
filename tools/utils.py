import asyncio
import datetime
import itertools
import math
from typing import Union
from urllib.parse import quote, unquote

from croniter import croniter
from pyrogram import Client


# 字节数转文件大小


def pybyte(size, dot=2):
    size = float(size)
    # 位 比特 bit
    if 0 <= size < 1:
        human_size = f"{str(round(size / 0.125, dot))}b"
    elif 1 <= size < 1024:
        human_size = f"{str(round(size, dot))}B"
    elif math.pow(1024, 1) <= size < math.pow(1024, 2):
        human_size = f"{str(round(size / math.pow(1024, 1), dot))}KB"
    elif math.pow(1024, 2) <= size < math.pow(1024, 3):
        human_size = f"{str(round(size / math.pow(1024, 2), dot))}MB"
    elif math.pow(1024, 3) <= size < math.pow(1024, 4):
        human_size = f"{str(round(size / math.pow(1024, 3), dot))}GB"
    elif math.pow(1024, 4) <= size < math.pow(1024, 5):
        human_size = f"{str(round(size / math.pow(1024, 4), dot))}TB"
    else:
        raise ValueError(
            f"{pybyte.__name__}() takes number than or equal to 0, but less than 0 given."
        )
    return human_size


# 列表/字典key翻译，输入：待翻译列表/字典，翻译字典 输出：翻译后的列表/字典
def translate_key(
    list_or_dict: list | dict, translation_dict: dict
):  # sourcery skip: assign-if-exp
    if isinstance(list_or_dict, dict):

        def translate_zh(_key):
            translate_dict = translation_dict
            # 如果翻译字典里有当前的key，就返回对应的中文字符串
            if _key in translate_dict:
                return translate_dict[_key]
            # 如果翻译字典里没有当前的key，就返回原字符串
            else:
                return _key

        new_dict_or_list = {}  # 存放翻译后key的字典
        # 遍历原字典里所有的键值对
        for key, value in list_or_dict.items():
            # 如果当前的值还是字典，就递归调用自身
            if isinstance(value, dict):
                new_dict_or_list[translate_zh(key)] = translate_key(
                    value, translation_dict
                )
            # 如果当前的值不是字典，就把当前的key翻译成中文，然后存到新的字典里
            else:
                new_dict_or_list[translate_zh(key)] = value
    else:
        new_dict_or_list = []
        for index, value in enumerate(list_or_dict):
            if value in translation_dict.keys():
                new_dict_or_list.append(translation_dict[value])
            else:
                new_dict_or_list.append(value)
    return new_dict_or_list


# 解析cron表达式
def parse_cron(cron: str, ret_quantity: int = None) -> Union[str, list]:
    c = cron.split()
    if c[4] != "*":
        c[4] = str(int(c[4]) + 1)
    cron = " ".join(c)

    week_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    str_time_now = datetime.datetime.now()
    cron_iter = croniter(cron, str_time_now)

    def format_date(d):
        return (
            f"{d.strftime('%Y-%m-%d %H:%M:%S')} {week_list[int(d.strftime('%u')) - 1]}"
        )

    if ret_quantity is None:
        t = cron_iter.get_next(datetime.datetime)
        return format_date(t)
    else:
        dates = list(
            itertools.islice(cron_iter.all_next(datetime.datetime), ret_quantity)
        )
        formatted_dates = [format_date(d) for d in dates]
        return formatted_dates


def encode_url(url, mode=True):
    """
    如果已编码则不进行编码
    :param url:
    :param mode:True 编码，False 解码
    :return:
    """

    decoded_path = unquote(url)
    is_encode_url = url != decoded_path
    if mode:
        return url if is_encode_url else quote(url, safe=":/?#=&")
    else:
        return unquote(url) if is_encode_url else url


async def schedule_delete_messages(
    client: Client, chat_id: int, message_ids: int | list, delay_seconds: int = 2
):
    """定时删除消息"""

    await asyncio.sleep(delay_seconds)

    try:
        await client.delete_messages(chat_id, message_ids)
    except Exception:
        ...
