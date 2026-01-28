from django.conf import settings
from django.core.files.storage import FileSystemStorage

stall_storage = FileSystemStorage(
    location=settings.STALL_DATASET_DIR,
    base_url="/dataset/stall/"
)

stall_training_storage = FileSystemStorage(
    location=settings.STALL_TRAINING_DATASET_DIR,
    base_url="/dataset/stall/training/"
)