import os
from transformers import pipeline

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # cesta k souboru model.py (tedy složka scraper)
models_dir = os.path.join(BASE_DIR, "models", "facebook-bart-large-mnli")

classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
classifier.save_pretrained(models_dir)