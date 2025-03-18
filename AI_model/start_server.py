import os
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

from file_auto_txt import TextClassifierSystem
from file_auto_img import ImageClassifierSystem
import threading

if __name__ == "__main__":

    # Image server thread
    img_server = threading.Thread(
        target=ImageClassifierSystem(os.getcwd(), "train_files_img", num_labels=5).serve_model,
        kwargs={'host': '0.0.0.0', 'port': 8001}
    )

    # Text server thread
    txt_server = threading.Thread(
        target=TextClassifierSystem(os.getcwd(), "train_files_txt", num_labels=3).serve_model,
        kwargs={'host': '0.0.0.0', 'port': 8000}
    )

    img_server.start()
    txt_server.start()

    img_server.join()
    txt_server.join()