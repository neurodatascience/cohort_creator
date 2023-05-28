"""Update datasets list."""
from __future__ import annotations

from pathlib import Path
from warnings import warn

import pandas as pd
import requests
from datalad import api
from rich import print

USERNAME = "Remi-Gau"

TOKEN_FILE = Path("/home/remi/Documents/tokens/gh_read_repo_for_orga.txt")

OPENNEURO = "OpenNeuroDatasets"
OPENNEURO_DERIVATIVES = "OpenNeuroDerivatives"


def root_dir() -> Path:
    return Path(__file__).parent.parent


def known_datasets_tsv() -> Path:
    return root_dir() / "cohort_creator" / "data" / "openneuro_derivatives.tsv"


def gh_api_base_url() -> str:
    return "https://api.github.com/orgs/"


def request_list_of_repos(
    gh_orga: str, page: int, auth: tuple[str, str] | None = None
) -> dict[str, str] | None:
    url = f"{gh_api_base_url()}{gh_orga}/repos?per_page=100&page={page}"
    print(url)
    response = requests.get(url, auth=auth)
    if response.status_code != 200:
        warn(f"Error {response.status_code}: {response.text}")
        return None
    return response.json()


def get_list_of_datasets() -> list[str]:
    auth = get_auth()
    datasets: list[str] = []
    resp: dict[str, str] | None = {}
    page = 1
    while resp:
        resp = request_list_of_repos(OPENNEURO_DERIVATIVES, page=page, auth=auth)
        if resp is None:
            break
        datasets.extend(repo["name"] for repo in resp)  # type: ignore
        page += 1
    return datasets


def get_auth() -> tuple[str, str] | None:
    TOKEN = None
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE) as f:
            TOKEN = f.read().strip()
    auth = None if USERNAME is None or TOKEN is None else (USERNAME, TOKEN)
    return auth


def main() -> None:
    known_datasets = pd.read_csv(known_datasets_tsv(), sep="\t")
    print(known_datasets["name"].values)
    print(len(known_datasets))

    datasets = get_list_of_datasets()

    unknown_datasets = [
        repo
        for repo in datasets
        if repo.split("-")[0] not in known_datasets["name"].values and repo.startswith("ds")
    ]
    unknown_datasets = sorted(unknown_datasets)
    print(sorted(unknown_datasets))
    print(len(unknown_datasets))

    if not unknown_datasets:
        print("No new dataset found")
        return

    output_dir = Path(__file__).parent / "tmp"
    output_dir.mkdir(exist_ok=True)

    for dataset in unknown_datasets:
        print(f"Downloading {dataset}")
        data_pth = output_dir / dataset
        if data_pth.exists():
            print(f"  data already present at {data_pth}")
        else:
            print(f"    installing : {data_pth}")
            api.install(
                path=data_pth, source=f"https://github.com/{OPENNEURO_DERIVATIVES}/{dataset}"
            )


if __name__ == "__main__":
    main()
