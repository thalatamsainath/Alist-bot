from apscheduler.schedulers.asyncio import AsyncIOScheduler


# Define a singleton class
class Singleton:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance


# Define a class for APScheduler and inherit from the singleton class
class APS(Singleton):
    # Initialize the scheduler with specified settings
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        # Start the scheduler
        self.scheduler.start()

    # Add a job to the scheduler
    def add_job(
        self,
        job_id,
        func,
        trigger="cron",
        args=None,
        kwargs=None,
        name=None,
        **trigger_args
    ):
        """
        Add a job

        :param job_id: Job ID, used to uniquely identify the job, required
        :param func: Job execution function, required
        :param trigger: Trigger type, optional, default is cron expression
        :param args: Parameters for the job execution function, as a list, optional
        :param kwargs: Parameters for the job execution function, as a dictionary, optional
        :param name: Job name, optional
        :param trigger_args: Trigger parameters, optional
        :return: Returns True if the job is added successfully, False otherwise
        """
        # Check if the job ID already exists; if not, add the job, otherwise return False
        return not self.job_exists(job_id) and self.scheduler.add_job(
            id=job_id,
            func=func,
            trigger=trigger,
            args=args,
            kwargs=kwargs,
            name=name,
            **trigger_args,
        )

    # Modify an existing job in the scheduler
    def modify_job(
        self,
        job_id,
        func=None,
        trigger=None,
        args=None,
        kwargs=None,
        name=None,
        **trigger_args
    ):
        """
        Modify a job

        :param job_id: Job ID, required
        :param func: New job execution function, optional
        :param trigger: New trigger type, optional
        :param args: New parameters for the job execution function, as a list, optional
        :param kwargs: New parameters for the job execution function, as a dictionary, optional
        :param name: New job name, optional
        :param trigger_args: New trigger parameters, optional
        :return: Returns True if the job is modified successfully, False otherwise
        """
        # Check if the job ID exists; if it does, modify the job, otherwise return False
        return self.job_exists(job_id) and self.scheduler.reschedule_job(
            job_id=job_id,
            func=func,
            trigger=trigger,
            args=args,
            kwargs=kwargs,
            name=name,
            **trigger_args,
        )

    # Pause a job in the scheduler
    def pause_job(self, job_id):
        """
        Pause a job

        :param job_id: Job ID, required
        :return: Returns True if the job is paused successfully, False otherwise
        """
        # Check if the job ID exists; if it does, pause the job, otherwise return False
        return self.job_exists(job_id) and self.scheduler.pause_job(job_id)

    # Resume a paused job in the scheduler
    def resume_job(self, job_id):
        """
        Resume a job

        :param job_id: Job ID, required
        :return: Returns True if the job is resumed successfully, False otherwise
        """
        # Check if the job ID exists; if it does, resume the job, otherwise return False
        return self.job_exists(job_id) and self.scheduler.resume_job(job_id)

    # Remove a job from the scheduler
    def remove_job(self, job_id):
        """
        Remove a job

        :param job_id: Job ID, required
        :return: Returns True if the job is removed successfully, False otherwise
        """
        # Check if the job ID exists; if it does, remove the job, otherwise return False
        return self.job_exists(job_id) and self.scheduler.remove_job(job_id)

    def job_exists(self, job_id):
        # Check if the job exists and return a boolean value
        return bool(self.scheduler.get_job(job_id))


aps = APS()
