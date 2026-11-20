# Acquire the transaction data

The original classroom analysis uses `Market_Basket_Optimisation.csv`: a headerless
CSV with one basket per row and blank padding between variable-length baskets.
The local historical file has 7,501 nonempty baskets. It is **not redistributed**.

1. Visit the [SuperDataScience Machine Learning A–Z resource page](https://www.superdatascience.com/machine-learning).
2. Follow **Course Datasets**, obtain the materials under the provider's terms,
   and find `Market_Basket_Optimisation.csv` in the association-rule/Apriori materials.
3. Create `data/local/` and place that file there, or pass your acquired path with
   `python -m src.pipeline --data YOUR_PATH`.

The page links to a course archive. The [provider's terms, section 6.1](https://www.superdatascience.com/terms-conditions)
reserve rights in datasets and course materials; availability is not a general
redistribution license. No course archive, slides, code templates, raw transactions
or transaction previews are included here. No signup, credentials or download is
performed by this repository.

The pipeline records the acquired file's SHA-256 and dimensions in the aggregate
result receipt so different releases can be distinguished. Only use data you may
lawfully obtain. The small invented baskets in unit tests test arithmetic and are
not presented as a substitute dataset or portfolio experiment.

Provider links checked 20 November 2026. The original local file's upstream chain
was not recorded in the classroom notebook; the provider resource is a legitimate
acquisition route, not proof of the local file's complete history.
