from django.core.files.storage import Storage

from django.conf import settings


class FastDFSStorage(Storage):
    """自定义文件存储类"""

    def _open(self, name, mode="rb"):
        pass

    def _save(self, name, content):
        pass

    def url(self, name):
        return settings.FDFS_BASE_URL + name
