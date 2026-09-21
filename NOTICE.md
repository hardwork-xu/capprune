# Third-party notices and provenance

[简体中文](NOTICE_zh.md) · [License](LICENSE) · [Research references](docs/en/RESEARCH.md)

CapPrune's project code and documentation use the MIT license, copyright 2026 CapPrune contributors. This does not relicense dependencies, datasets, cited papers, or other third-party materials. Dependencies are installed separately; their original notices remain in their distributions.

The following metadata and license files were inspected in the locked development environment on 2026-09-21. This table describes the directly used packages and the numerical dependency SciPy, rather than replacing their complete license texts or every transitive notice.

| Package | Version | License / notice source within its installed distribution | Role |
|---|---|---|---|
| NumPy | 2.2.6 | BSD-3-Clause; `numpy-2.2.6.dist-info/LICENSE.txt` also includes bundled-library notices. | Arrays and dense numerical kernels. |
| threadpoolctl | 3.6.0 | BSD-3-Clause; `threadpoolctl-3.6.0.dist-info/licenses/LICENSE`. | Benchmark thread control. |
| scikit-learn | 1.7.2 | BSD-3-Clause; `scikit_learn-1.7.2.dist-info/licenses/COPYING`, including bundled notices. | Bundled digits dataset loader; not the indexing implementation. |
| SciPy | 1.18.1 | BSD-3-Clause; `scipy-1.18.1.dist-info/LICENSE.txt`, including bundled notices. | Transitive scientific dependency. |
| Matplotlib | 3.10.6 | Matplotlib license agreement, derived from the PSF license; `matplotlib-3.10.6.dist-info/LICENSE`. Fonts have separate notices. | Experiment plots. |
| pyparsing | 3.2.3 | MIT; `pyparsing-3.2.3.dist-info/LICENSE`. | Pinned plotting-parser dependency. |
| psutil | 7.1.0 | BSD-3-Clause; `psutil-7.1.0.dist-info/LICENSE`. | Process memory measurements. |
| pytest | 8.4.2 | MIT; distribution `licenses/LICENSE`. | Tests. |
| Ruff | 0.13.0 | MIT; distribution `licenses/LICENSE`. | Formatting and linting. |
| mypy | 1.18.1 | MIT; distribution `licenses/LICENSE`; bundled typeshed has its own notice. | Type checking. |
| build | 1.3.0 | MIT; distribution `licenses/LICENSE`. | Build frontend. |
| hatchling | 1.27.0 | MIT; distribution `licenses/LICENSE.txt`. | Build backend. |

The [lockfile](uv.lock) records all resolved versions and artifact hashes. When redistributing dependency binaries or a container, preserve their included license and attribution files. This repository's source distribution does not vendor those dependency binaries. Standard MIT text is retained in English; the project explanation is available in both languages.

## Dataset attribution

The real-data benchmark calls `sklearn.datasets.load_digits` from scikit-learn 1.7.2. Its [official versioned documentation](https://scikit-learn.org/1.7/modules/generated/sklearn.datasets.load_digits.html) identifies 1,797 digit images represented by 64 numeric features, drawn from the UCI dataset's test portion. CapPrune takes 40 held-out query rows and 1,757 database rows, then normalizes the numeric features for cosine retrieval. This is not a pretrained embedding dataset or a classification-accuracy experiment. Dataset arrays are not copied into this repository.

Attribution: **Alpaydin, E. and Kaynak, C. (1998). Optical Recognition of Handwritten Digits. UCI Machine Learning Repository. [DOI: 10.24432/C50P49](https://doi.org/10.24432/C50P49).** The [UCI dataset page](https://archive.ics.uci.edu/dataset/80/optical+recognition+of+handwritten+digits) lists [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). These primary pages were checked on 2026-09-21.

All clustered and isotropic benchmark cases are generated synthetic vectors, with seeds and configuration recorded in results. No personal dataset or model weights are included.

## Algorithm attribution and citation

Angular branch-and-bound and spherical k-means are established methods, attributed with source links in [RESEARCH.md](docs/en/RESEARCH.md). CapPrune does not claim those algorithms as original, and this notice does not imply affiliation with or endorsement by the cited authors or projects.

For this software, use the descriptive citation: **CapPrune: exact cosine retrieval with spherical-cap block pruning, version 0.1.0 (2026), software.** Include the source revision or artifact SHA-256 used in the experiment. No DOI, publication venue, public repository URL, or individual author metadata is assigned here. `CITATION.cff` is omitted until its required public authorship metadata is verified.
