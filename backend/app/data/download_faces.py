"""
Downloads a small subset of LFW (Labeled Faces in the Wild) dataset
for use as mock missing persons database.
Run once: python -m app.data.download_faces
"""
import os
import urllib.request

# 20 sample face image URLs from LFW dataset (public domain)
SAMPLE_FACES = [
    ("Aaron_Eckhart", "https://vis-www.cs.umass.edu/lfw/images/Aaron_Eckhart/Aaron_Eckhart_0001.jpg"),
    ("Aaron_Guiel", "https://vis-www.cs.umass.edu/lfw/images/Aaron_Guiel/Aaron_Guiel_0001.jpg"),
    ("Aaron_Patterson", "https://vis-www.cs.umass.edu/lfw/images/Aaron_Patterson/Aaron_Patterson_0001.jpg"),
    ("Aaron_Peirsol", "https://vis-www.cs.umass.edu/lfw/images/Aaron_Peirsol/Aaron_Peirsol_0001.jpg"),
    ("Aaron_Sorkin", "https://vis-www.cs.umass.edu/lfw/images/Aaron_Sorkin/Aaron_Sorkin_0001.jpg"),
    ("Abba_Eban", "https://vis-www.cs.umass.edu/lfw/images/Abba_Eban/Abba_Eban_0001.jpg"),
    ("Abbas_Kiarostami", "https://vis-www.cs.umass.edu/lfw/images/Abbas_Kiarostami/Abbas_Kiarostami_0001.jpg"),
    ("Abdel_Nasser_Assidi", "https://vis-www.cs.umass.edu/lfw/images/Abdel_Nasser_Assidi/Abdel_Nasser_Assidi_0001.jpg"),
    ("Abdullah_Ahmad_Badawi", "https://vis-www.cs.umass.edu/lfw/images/Abdullah_Ahmad_Badawi/Abdullah_Ahmad_Badawi_0001.jpg"),
    ("Adel_Smith", "https://vis-www.cs.umass.edu/lfw/images/Adel_Smith/Adel_Smith_0001.jpg"),
]

def download_faces():
    save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "faces")
    os.makedirs(save_dir, exist_ok=True)

    print(f"Downloading {len(SAMPLE_FACES)} sample faces to {save_dir}...")

    for name, url in SAMPLE_FACES:
        filename = f"{name}.jpg"
        filepath = os.path.join(save_dir, filename)

        if os.path.exists(filepath):
            print(f"  ✓ {filename} already exists, skipping.")
            continue

        try:
            urllib.request.urlretrieve(url, filepath)
            print(f"  ✓ Downloaded {filename}")
        except Exception as e:
            print(f"  ✗ Failed {filename}: {e}")

    print(f"\n✅ Done. Faces saved to app/data/faces/")

if __name__ == "__main__":
    download_faces()