from loguru import logger
from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from api.cloudflare.cloudflare_api import CloudflareAPI
from config.config import CloudFlareInfo, cf_cfg, chat_data
from tools.filters import is_admin

tmp_account_workers_pages = {}


# cf账号管理按钮回调
@Client.on_callback_query(filters.regex("^account_add$"))
async def account_add_callback(_, query: CallbackQuery):
    await account_add(query)
    chat_data["ad_message"] = query


# 添加/删除账号
async def account_add(query: CallbackQuery):
    text = []
    chat_data["account_add_return_button"] = [
        InlineKeyboardButton("↩️ Return to account", callback_data="account_return"),
        InlineKeyboardButton("❌ Close menu", callback_data="cf_close"),
    ]
    if nodes := cf_cfg.nodes:
        for index, value in enumerate(nodes):
            text_t = f"{index + 1} | <code>{value.email}</code> | <code>{value.global_api_key}</code>\n"
            text.append(text_t)
        t = "\n".join(text)
    else:
        t = "No account yet"
    tt = """
——————————————
<b>Add:</b>
Only one account can be added at a time
The first line is cf email address, the second line is global_api_key, for example:
<code>abc123@qq.com
285812f3012365412d33398713c156e2db314
</code>
<b>Delete:</b>
*+serial number, for example: <code>*2</code>
"""
    await query.message.edit(
        text=t + tt,
        reply_markup=InlineKeyboardMarkup([chat_data["account_add_return_button"]]),
    )
    chat_data["account_add"] = True


def _account_add_filter(_, __, ___):
    return bool("account_add" in chat_data and chat_data["account_add"])


account_add_filter = filters.create(_account_add_filter)


async def url_select(query: CallbackQuery):
    exist_ids = [node.account_id for node in cf_cfg.nodes]
    index = 0
    t = "Domain List\n"
    chat_data["url_select_return_button"] = []
    for key, value in tmp_account_workers_pages.items():
        for k, v in value.items():
            if v.account_id in exist_ids:
                tmp_account_workers_pages.pop(key)
                return await url_select(query)
            if index % 3 == 0:
                chat_data["url_select_return_button"].append([])
            chat_data["url_select_return_button"][-1].append(
                InlineKeyboardButton(v.url, callback_data=k)
            )
            index += 1
            t += f"{index} | <code>{v.url}</code>\n"
        chat_data["url_select_return_button"].append(
            [InlineKeyboardButton("Cancel", callback_data=key)]
        )
        break

    tt = """
——————————————
<b>Choose a domain name</b>
One worker/page can only be bound to one domain name.
"""
    await query.message.edit(
        text=t + tt,
        reply_markup=InlineKeyboardMarkup(chat_data["url_select_return_button"]),
    )


@Client.on_callback_query(filters.regex("^(work|page)-(.*)$"))
async def work_page_callback(_, query: CallbackQuery):
    data = query.data
    if data in tmp_account_workers_pages:
        tmp_account_workers_pages.pop(data)
    else:
        for key, value in tmp_account_workers_pages.items():
            if data in value:
                d = value.pop(data)
                tmp_account_workers_pages.pop(key)
                cf_cfg.add_node(d)
                break
    # await chat_data["ad_message"].answer(text="添加成功")
    if tmp_account_workers_pages:
        await url_select(query)
    else:
        await account_add(query)


# 开始处理
@Client.on_message(filters.text & account_add_filter & filters.private & is_admin)
async def account_edit(_, message: Message):
    mt = message.text
    await message.delete()
    if mt[0] != "*":
        try:
            exist_ids = [node.account_id for node in cf_cfg.nodes]
            email, global_api_key = mt.split("\n")[:2]
            cf = CloudflareAPI(email, global_api_key)
            accounts = await cf.list_accounts()
            account_workers_pages = []
            for account in accounts.result:
                account_id = account["id"]
                if account_id in exist_ids:
                    continue
                lw = await cf.list_workers(account_id)
                # lw: AsyncSinglePage[Script] = AsyncSinglePage[Script](result=[])
                lp = await cf.list_pages(account_id)
                # lp: AsyncSinglePage[Deployment] = AsyncSinglePage[Deployment](result=[])
                if len(lw.result) > 0 or len(lp.result) > 0:
                    account_workers_pages.append((account_id, lw.result, lp.result))
        except Exception as e:
            logger.error(f"Error: {type(e)} {str(e)}")
            await chat_data["ad_message"].answer(text=f"Error: {str(e)}")
        else:
            if account_workers_pages:
                for account, workers, pages in account_workers_pages:
                    for worker in workers:
                        worker_name = worker.id
                        if worker.routes:
                            for route in worker.routes:
                                url = route["pattern"].rstrip("/*")
                                key = f"work-{account[:7]}-{worker_name[:7]}"
                                if tmp_account_workers_pages.get(key) is None:
                                    tmp_account_workers_pages[key] = {}
                                tmp_account_workers_pages[key][f"{key}-{url[:7]}"] = (
                                    CloudFlareInfo(
                                        url=url,
                                        email=email,
                                        global_api_key=global_api_key,
                                        account_id=account,
                                        worker_name=worker_name,
                                        page_name="",
                                    )
                                )
                    for page in pages:
                        page_name = page.production_script_name
                        if page.latest_deployment["aliases"]:
                            url = page.latest_deployment["aliases"][0]
                            url = url.lstrip("http://").lstrip("https://")
                            key = f"page-{account[:7]}-{page_name[:7]}"
                            if tmp_account_workers_pages.get(key) is None:
                                tmp_account_workers_pages[key] = {}
                            tmp_account_workers_pages[key][f"{key}-{url[:7]}"] = (
                                CloudFlareInfo(
                                    url=url,
                                    email=email,
                                    global_api_key=global_api_key,
                                    account_id=account,
                                    worker_name="",
                                    page_name=page_name,
                                )
                            )
                await url_select(chat_data["ad_message"])
            else:
                text = f"""
<b>Add failed: </b>

<code>{mt}</code>

The Workers route is not added to this domain (<code>{account_workers_pages}</code>)

Please check and resend the account

<b>Note:</b> The first Workers route of the first domain is used by default
"""
                await chat_data["ad_message"].message.edit(
                    text=text,
                    reply_markup=InlineKeyboardMarkup(
                        [chat_data["account_add_return_button"]]
                    ),
                )

    else:
        i = int(mt.split("*")[1])
        nodes = cf_cfg.nodes
        cf_cfg.del_node(nodes[i - 1])
        await account_add(chat_data["ad_message"])
