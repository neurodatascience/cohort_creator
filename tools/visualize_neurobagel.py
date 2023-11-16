"""Plot basic visualization of the content of the opendata neurobagel graph.

Only concerns openneuro for now.

Required inuput:
- participant-level-results.tsv for the whole neurobagel graph
  that can be obtained by running an empty query in
  https://query.neurobagel.org/
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px

input_file = Path(__file__).parent / "participant-level-results.tsv"

df = pd.read_csv(input_file, sep="\t")

# remove protected
mask = df["Age"] != "protected"
df = df[mask]

df = df.replace("http://purl.bioontology.org/ontology/SNOMEDCT/248153007", "M")
df = df.replace("http://purl.bioontology.org/ontology/SNOMEDCT/248152002", "F")

mask = df["Sex"].apply(lambda x: x in ["M", "F"])
df = df[mask]

df["Age"] = df["Age"].astype(float)

# remove duplicates
record_ID = df["DatasetID"] + df["SubjectID"]
present = []
mask = []
for i in record_ID:
    if i in present:
        mask.append(False)
    else:
        mask.append(True)
        present.append(i)
df = df[mask]

nb_datasets = len(set(df["DatasetID"].to_list()))

fig = px.histogram(
    df.round(),
    x="Age",
    color="Sex",
    title=f"Age distribution ({nb_datasets} MRI datasets from openneuro)",
)

fig.show()
