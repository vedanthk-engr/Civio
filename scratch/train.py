import os
import csv
import pickle
import pathlib
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

# Paths
source_csv = pathlib.Path("v:/Project/Civio/Areapulse-main/Areapulse-main/models/master_dataset.csv")
dest_pkl = pathlib.Path("v:/Project/Civio/backend/models/spam_clf.pkl")

print(f"Reading dataset from {source_csv}...")
df = pd.read_csv(source_csv)

print("Training Pipeline...")
pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(max_features=2500, ngram_range=(1, 2))),
    ('clf', LogisticRegression(C=1.5, max_iter=200))
])

# Fit
pipeline.fit(df['text'], df['label'])

print(f"Saving model to {dest_pkl}...")
os.makedirs(dest_pkl.parent, exist_ok=True)
with open(dest_pkl, 'wb') as f:
    pickle.dump(pipeline, f)

print("Trained successfully!")
