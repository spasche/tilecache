from threading import Thread
from boto import s3

class Uploader(Thread):
    def __init__(self, queue, access_key, secret_access_key, bucket_name):
        Thread.__init__(self)
        self.queue = queue
        self.aws_access = (access_key, secret_access_key)
        self.bucket_name = bucket_name
        self._bucket = None

    @property
    def bucket(self):
        if self._bucket is None:
            self._bucket = s3.connection.S3Connection(*self.aws_access).get_bucket(self.bucket_name)
        return self._bucket

    def run(self):
        while True:
            name, data, policy, headers = self.queue.get()

            key = s3.key.Key(self.bucket)
            key.name = name
            key.set_contents_from_string(data, headers=headers, policy=policy)

            self.queue.task_done()
