# Dataset Exploration Mini-Report

**Project P05 — Distributed Analysis of Customer Reviews and Trends**
Amazon Reviews 2023 (Appliances), Hadoop MapReduce and Lakehouse

| Item | Detail |
|---|---|
| Programme | Master 1 — Artificial Intelligence & Data Science, ISIMa (University of Monastir) |
| Module | Big Data |
| Supervisor | Dr. Ing. Takwa Ben Aïcha Gader |
| Academic year | 2026/2027 |
| Group members | *[to be completed]* |
| Report date | 3 November 2026 |
| Report type | Exploratory analysis only (no cleaning, no modification of the data) |

---

## 1. Introduction

Project P05 builds a distributed analytics platform for customer reviews. The platform uses three Java Hadoop MapReduce jobs (MR1: term frequencies, MR2: TF-IDF per product, MR3: monthly rating trends) and publishes the results in Apache Iceberg tables. The engineering question of the project is: *how can we link the recurring themes in reviews to changes in ratings for each product, while keeping the distributed calculations traceable?*

Before building this pipeline, we need to know what the data looks like. This report presents the **first technical exploration** of the *Appliances* subset of Amazon Reviews 2023. Its goals are:

- to describe the size, structure and content of the dataset;
- to find features that will influence the design of the pipeline (for example, skewed ratings, very short texts, products with few reviews);
- to list questions that must be answered in the next stage (HDFS Bronze and data preparation).

**Important notes about the scope of this report**

- This is an **exploratory analysis**. It describes the data as it is. It is **not** a data-cleaning step.
- **The original dataset was not modified.** All statistics were calculated by reading the file in streaming mode.
- **No record was rejected or corrected** during exploration.
- **Duplicate detection and definitive data validation are reserved for the preparation stage.**
- This report only uses the results produced by the exploration script (JSON summary, CSV files and charts). No new statistics were calculated while writing it.

---

## 2. Dataset source and description

### 2.1 Source

The dataset comes from **Amazon Reviews 2023**, published by the McAuley Lab (UC San Diego). The P05 specification gives the following references:

| Item | Reference |
|---|---|
| Official portal | https://amazon-reviews-2023.github.io/main.html |
| Hugging Face repository | https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023 |
| Scientific reference | Hou et al., *Bridging Language and Items for Retrieval and Recommendation* (2024), https://arxiv.org/abs/2403.03952 |
| Selected category | *Appliances* (reviews file: `Appliances.jsonl.gz`) |
| Product metadata (optional) | `meta_Appliances.jsonl.gz` — **not analysed in this report** |

### 2.2 Format and intended use

- **Format:** JSON Lines (one review per line), UTF-8 encoding.
- **Language:** mainly English. The pipeline is designed for English text.
- **Usage:** the dataset is used for an educational project. The terms of use of the provider must be checked before any redistribution. User identifiers must not be shown in dashboards (P05, sections 6.1–6.2 and NF05).

### 2.3 Position of the dataset in the P05 pipeline

The raw files will be stored in the **Bronze** zone of HDFS, cleaned in the **Silver** zone, and the results of MR1, MR2 and MR3 will be published in **Gold** Iceberg tables. This exploration is the step that comes just before the Bronze ingestion.

---

## 3. Dataset overview

The table below summarises the main figures from `dataset_summary.json`.

| Characteristic | Value |
|---|---|
| Dataset name | Amazon Reviews 2023 — Appliances |
| Format / encoding | JSON Lines / UTF-8 |
| File size | 929,451,412 bytes (886.394 MB, about 0.866 GB) |
| Total lines | 2,128,605 |
| Empty lines | 0 |
| Invalid JSON lines | 0 |
| Valid JSON objects | 2,128,605 |
| Non-object JSON values | 0 |
| Unique `parent_asin` (products) | 94,319 |
| Unique `asin` (variants) | 104,237 |
| Earliest review date | 2000-10-23 |
| Latest review date | 2023-09-12 |
| Average rating | 4.2215 |
| Median rating | 5.0 |

**Interpretation.** Every line of the file is a valid JSON object, so the file can be read without parsing errors. The number of reviews (about 2.1 million) and the number of products (about 94,300) match the order of magnitude given in the P05 specification. There are more `asin` values (104,237) than `parent_asin` values (94,319). This is expected, because several variants (`asin`) can belong to one product group (`parent_asin`). As required by P05, `parent_asin` is the product key used in this project, and the two identifiers must not be confused.

The date range goes from October 2000 to September 2023, which is more than 22 years of reviews.

---

## 4. JSON schema analysis

The script scanned all 2,128,605 records and recorded the type of each top-level field.

| Field | Observed type | Records with the field | Missing field | Null values |
|---|---|---|---|---|
| `asin` | string | 2,128,605 | 0 | 0 |
| `helpful_vote` | integer | 2,128,605 | 0 | 0 |
| `images` | array | 2,128,605 | 0 | 0 |
| `parent_asin` | string | 2,128,605 | 0 | 0 |
| `rating` | float | 2,128,605 | 0 | 0 |
| `text` | string | 2,128,605 | 0 | 0 |
| `timestamp` | integer | 2,128,605 | 0 | 0 |
| `title` | string | 2,128,605 | 0 | 0 |
| `user_id` | string | 2,128,605 | 0 | 0 |
| `verified_purchase` | boolean | 2,128,605 | 0 | 0 |

**Observations**

- The file has **10 top-level fields**, and each one has a single observed type. No field has mixed types.
- The fields needed by P05 are all present: `parent_asin`, `asin`, `text`, `title`, `rating`, `timestamp`, `verified_purchase`, `helpful_vote` and `user_id`.
- `images` is a list of images. P05 says that image data is **not** required, so this field will not be used.
- `user_id` is a potentially sensitive field. It must be kept out of dashboards and exports (P05, NF05).
- `timestamp` is stored as an integer. The exploration script interpreted it as **Unix milliseconds**. This interpretation gives dates between 2000 and 2023 (including a latest value with a fractional second), which is a reasonable range for this dataset. P05 asks the team to check the real unit on concrete values, so this should be confirmed again in the preparation stage.

> **Limit of this analysis.** The schema table only describes the *top-level* fields and their types. The supplied results do not show the content inside the `images` arrays, and they do not show value ranges for `helpful_vote` or the distribution of `verified_purchase`.

---

## 5. Missing values analysis

### 5.1 Field-level completeness

For all 10 fields, the number of missing fields is **0**, the number of null values is **0**, and the missing-or-null percentage is **0.0%**.

### 5.2 Empty text

A field can be present and not null but still contain no useful content. The text statistics show this case for the `text` field:

| Indicator | Value |
|---|---|
| Records where `text` is present as a string | 2,128,605 |
| Reviews with an **empty** text | 2,065 |
| Reviews with a valid (non-empty) text | 2,126,540 |

**Interpretation.** The `text` field is never missing or null, but 2,065 reviews contain an empty text. This shows that a "missing/null" check alone is not enough: the preparation stage must also test for empty content. P05 already requires this control ("contenu textuel non vide") and asks the team to count every rejection by reason.

### 5.3 Other fields

The supplied results do **not** include a check for empty strings in `title`, `parent_asin`, `asin` or `user_id`. The report therefore makes no statement about them. The JSON summary shows `missing_parent_asin = 0`, `invalid_rating = 0`, `missing_timestamp = 0` and `invalid_timestamp = 0`.

> **Note.** These results describe the file as it is. They do not mean the data is ready to use. Final validation rules and rejection counts will be produced during preparation.

---

## 6. Customer rating analysis

### 6.1 Rating distribution

| Rating | Number of reviews | Percentage |
|---|---|---|
| 1.0 | 250,453 | 11.766% |
| 2.0 | 79,664 | 3.743% |
| 3.0 | 104,047 | 4.888% |
| 4.0 | 208,216 | 9.782% |
| 5.0 | 1,486,225 | 69.822% |

| Summary indicator | Value |
|---|---|
| Valid ratings | 2,128,605 |
| Invalid ratings | 0 |
| Average rating | 4.2215 |
| Median rating | 5.0 |

![Distribution of customer ratings](figures/rating_distribution.png)

*Figure 1 — Distribution of customer ratings.*

### 6.2 Explanation

- All ratings in the file are valid, and the observed values are 1.0, 2.0, 3.0, 4.0 and 5.0. This matches the P05 requirement that ratings are in the range [1, 5].
- The distribution is **strongly unbalanced**. The 5-star rating is by far the most frequent (69.822%). The median is 5.0, and the average (4.2215) is lower than the median because of the group of 1-star reviews.
- The shape is **not a smooth curve**. The 1-star group (11.766%) is larger than the 2-star (3.743%), 3-star (4.888%) and 4-star (9.782%) groups. In other words, customers in this dataset tend to give extreme ratings, either very positive or very negative.

### 6.3 Consequences for P05

- **MR3 (monthly trends):** monthly averages will probably be high for most products. Differences between products or months may be small, so counts per month must always be shown with the averages.
- **Rating classes:** the P05 classes (1–2 = low, 3 = neutral, 4–5 = high) will be very unequal in size. The neutral class is the smallest of the three groups in the supplied distribution.
- **Optional classifier (Naive Bayes / logistic regression):** if a group chooses this extension, the imbalance must be handled, and results must be compared to a majority-class baseline, as P05 requires.
- As P05 states, star ratings are **rating indicators**, not a ground truth of textual sentiment.

---

## 7. Temporal analysis

### 7.1 Reviews per year

| Year | Reviews | | Year | Reviews |
|---|---|---|---|---|
| 2000 | 1 | | 2012 | 15,219 |
| 2002 | 1 | | 2013 | 43,618 |
| 2003 | 8 | | 2014 | 77,353 |
| 2004 | 16 | | 2015 | 122,696 |
| 2005 | 80 | | 2016 | 153,916 |
| 2006 | 182 | | 2017 | 169,785 |
| 2007 | 621 | | 2018 | 189,599 |
| 2008 | 883 | | 2019 | 261,004 |
| 2009 | 1,539 | | 2020 | 311,251 |
| 2010 | 3,537 | | 2021 | 345,120 |
| 2011 | 7,636 | | 2022 | 299,487 |
| | | | 2023 | 125,053 |

The yearly file has 23 rows. The year 2001 is not listed, so no review is recorded for that year in the supplied results.

### 7.2 Reviews per month

The monthly file has 242 rows (one row per month that has at least one review). The chart below shows the monthly review volume.

![Monthly review volume](figures/monthly_review_volume.png)

*Figure 2 — Monthly review volume.*

> **Readability note.** On the supplied chart, the labels of the x-axis overlap and cannot be read. For the final project documentation, the axis labels should be improved. This report uses the values from `monthly_reviews.csv` instead of reading dates from the chart.

### 7.3 Explanation

- **Very few reviews before 2010.** From 2000 to 2009, the yearly counts stay below 2,000. The first two years with data have only one review each. These periods are too sparse for reliable trend analysis. This matches the P05 warning about low monthly counts in MR3.
- **Strong growth from 2010 to 2021.** The yearly count rises from 3,537 (2010) to 345,120 (2021), which is the highest yearly value in the supplied results.
- **Step increases in the monthly data.** In `monthly_reviews.csv`, the count jumps from 1,830 (November 2012) to 3,506 (December 2012), and from 4,303 (June 2014) to 7,794 (July 2014). The reasons for these jumps were not investigated and are unknown.
- **Peaks around the turn of the year.** In several years (for example 2016–2017, 2018–2019, 2020–2021), the monthly counts in December and January are higher than in the months before. This pattern was observed visually in the supplied values and was not tested statistically. The highest monthly value in the file is 36,838 reviews (March 2021).
- **Decline in 2022 and 2023.** The yearly count falls from 345,120 (2021) to 299,487 (2022).
- **2023 is an incomplete year.** The latest review in the dataset is dated 12 September 2023, so the 2023 value (125,053) covers only part of the year. In the monthly data, the counts drop strongly after March 2023 (28,510 in March, then 16,843, 9,831, 6,211, 4,888, 3,336, and only 198 in September 2023). The last months are therefore not comparable with the earlier months and should not be read as a real fall in customer activity.
- **Months without reviews.** Because the monthly file has 242 rows, some months in the date range have no row. For example, the first rows jump from October 2000 to November 2002. For MR3, such months must be shown as **absent**, not as zero ratings (P05, section 8.3).

---

## 8. Review text analysis

### 8.1 Text statistics

| Indicator | Value |
|---|---|
| Reviews with valid text | 2,126,540 |
| Reviews with empty text | 2,065 |
| Short reviews (5 words or fewer) | 440,241 |
| Total characters | 360,825,212 |
| Total words | 67,041,662 |
| Average length (characters) | 169.68 |
| Median length (characters) | 88 |
| Minimum / maximum length (characters) | 1 / 30,004 |
| Average length (words) | 31.53 |
| Median length (words) | 16 |
| Minimum / maximum length (words) | 1 / 3,636 |

![Distribution of review text length](figures/text_length_distribution.png)

*Figure 3 — Distribution of review text length (characters per review).*

### 8.2 Explanation

- **Most reviews are short.** The median review has 88 characters and 16 words. A review of this size is only one or two sentences.
- **The distribution is right-skewed.** The average (169.68 characters, 31.53 words) is much higher than the median (88 characters, 16 words). The histogram confirms this: almost all reviews are in the first bin, and a very thin tail extends up to 30,004 characters (3,636 words). A small number of very long reviews pull the average upward.
- **Many reviews are very short.** The dataset contains 440,241 reviews with at most 5 words. These reviews carry little lexical information, so they will have limited influence on MR1 and MR2 results.
- **Very long reviews exist.** Some reviews are much longer than the typical one. This is important for the preparation stage, for example to check processing time and memory use per line.
- **Total volume of text.** The corpus contains about 67 million words, which is large enough to justify a distributed approach with MapReduce.

### 8.3 Consequences for P05

- The TF-IDF "document" is the **set of cleaned reviews of one product** (P05, section 6.3), so short reviews are partly compensated when many reviews are combined for the same product. For products with few reviews, however, the term scores can be unstable. The P05 minimum support threshold (20 reviews, configurable) is therefore important.
- The supplied results do **not** describe the vocabulary: there is no list of frequent words, no language detection and no analysis of special characters or non-English text. These points are open questions for the preparation stage.
- The text statistics were computed on the raw text. They will change after normalisation, tokenisation and stop-word removal.

---

## 9. Product-level analysis

### 9.1 Most reviewed products

| Rank | `parent_asin` | Reviews |
|---|---|---|
| 1 | B0B3DB5HTC | 12,027 |
| 2 | B07RNJY499 | 11,620 |
| 3 | B07WTXWC32 | 8,519 |
| 4 | B08YBGCNHP | 7,330 |
| 5 | B000AST3AK | 7,030 |
| 6 | B01KJ2FVFW | 6,140 |
| 7 | B00UXG4WR8 | 5,896 |
| 8 | B000DLB2FI | 5,736 |
| 9 | B081KSD3BK | 5,668 |
| 10 | B09YC8YCV6 | 5,401 |
| 11 | B01BIDPHYQ | 5,299 |
| 12 | B0045LLC7K | 5,243 |
| 13 | B002JAKRAM | 5,042 |
| 14 | B092LLM7H3 | 5,040 |
| 15 | B07CP1KY9M | 5,010 |
| 16 | B09SHVMDY8 | 4,938 |
| 17 | B0BVFQY9HH | 4,874 |
| 18 | B09VTZ54J7 | 4,847 |
| 19 | B0C5PR3NWJ | 4,742 |
| 20 | B07P3Y8JWY | 4,533 |

![Top 20 most reviewed products](figures/top_20_products.png)

*Figure 4 — Top 20 most reviewed products.*

### 9.2 Reviews per product (distribution)

The file `reviews_per_product_distribution.csv` has 936 rows. Each row gives a number of reviews and the number of products that have exactly that number of reviews. A selection of rows is shown below.

| Reviews per product | Number of products |
|---|---|
| 1 | 33,588 |
| 2 | 12,587 |
| 3 | 7,314 |
| 4 | 4,936 |
| 5 | 3,642 |
| 10 | 1,350 |
| 20 | 505 |
| 50 | 115 |
| 100 | 45 |
| 12,027 (maximum) | 1 |

*The full table is available in `reviews_per_product_distribution.csv`.*

### 9.3 Explanation

- **The distribution is extremely unequal (long tail).** The group with exactly one review is the largest one: 33,588 products out of 94,319. The number of products falls quickly as the number of reviews grows, and the highest values (up to 12,027 reviews) are reached by a single product each.
- **A few products have many reviews.** The most reviewed product (B0B3DB5HTC) has 12,027 reviews, and the second (B07RNJY499) has 11,620. After the third product (8,519), the counts decrease more slowly in the top 20, ending at 4,533.
- **Consequence for MapReduce.** The P05 specification lists "skew de produits populaires" as a risk: a reducer that receives a very popular `(parent_asin, term)` key will do much more work than others. The supplied distribution confirms that this risk is real. It supports the use of a Combiner in MR1 and MR3, and it requires a justified decision about a Partitioner.
- **Consequence for interpretation.** Many products have very few reviews. TF-IDF scores and monthly averages for these products would be unreliable. The P05 rule to display the number of reviews per product and to hide products below a minimum (20 reviews by default, configurable) is therefore necessary.
- **Open point.** The supplied results do not give the number of products above the 20-review threshold. This number must be calculated later, in the preparation stage, because it directly affects the size of the analysable corpus.

---

## 10. Preliminary data quality observations

This section lists what the exploration shows. It is **not** a validation and **not** a cleaning step.

### 10.1 Positive observations

| Check | Result |
|---|---|
| Lines that are not valid JSON | 0 |
| Empty lines | 0 |
| Records that are not JSON objects | 0 |
| Missing `parent_asin` | 0 |
| Invalid ratings | 0 |
| Missing or invalid timestamps | 0 |
| Missing or null fields (all 10 fields) | 0 |

### 10.2 Points that need attention

| Observation | Why it matters | Planned stage |
|---|---|---|
| 2,065 reviews have an empty `text` | P05 requires non-empty text for NLP jobs | Preparation (reject and count by reason) |
| 440,241 reviews have 5 words or fewer | Low lexical information; may add noise to MR1/MR2 | Preparation (define and document a policy) |
| Very long reviews (up to 3,636 words) | Possible effect on processing time and memory | Preparation / tests |
| Strongly imbalanced ratings | Affects interpretation of means and any classifier | MR3 design, optional extension |
| Very sparse early years and incomplete 2023 | Unreliable monthly trends in these periods | MR3 and dashboard (low-count warnings) |
| Many products with one or a few reviews | Unstable TF-IDF and monthly averages | Minimum support threshold |
| Strong skew toward a few products | Reducer imbalance | Combiner, Partitioner analysis |
| `timestamp` unit was assumed to be milliseconds | Wrong unit would create wrong months in MR3 | Preparation (verify on concrete values) |
| `user_id` is present | Personal-data risk | Do not expose; anonymise if needed |

### 10.3 What has **not** been checked

The following checks were **not performed** during this exploration (the summary states that duplicate detection is reserved for the preparation stage), so no conclusion is possible:

- **duplicate reviews** (no duplicate check was done);
- consistency between `asin` and `parent_asin`;
- the distribution of `verified_purchase` and `helpful_vote`;
- the content of `title` (for example, empty titles);
- the language and character set of the texts;
- the product metadata file (`meta_Appliances.jsonl.gz`);
- the relation between ratings and review length, or between ratings and time.

> **Statement.** This report does **not** claim that the dataset is clean. The data is only described as it was received. The original file was not modified, and no record was rejected during exploration.

---

## 11. Main findings

1. **Large and structurally consistent dataset.** The file has 2,128,605 lines, all of them valid JSON objects, with the same 10 top-level fields and one observed type per field.
2. **Complete fields, but not complete content.** No field is missing or null, but 2,065 reviews have an empty text. Presence of a field does not mean usable content.
3. **Ratings are strongly positive and polarised.** 69.822% of reviews have 5 stars, the median is 5.0 and the average is 4.2215. The 1-star group (11.766%) is larger than the 2-, 3- and 4-star groups.
4. **Review activity grew fast, then changed.** Yearly volume increased from 3,537 reviews (2010) to a maximum of 345,120 (2021). 2022 was lower (299,487), and 2023 is incomplete (data until 12 September 2023).
5. **Early periods are sparse.** Before 2010, yearly counts are below 2,000, and some months have no reviews. Monthly trends in these periods will not be reliable.
6. **Reviews are mostly short.** The median is 16 words and 88 characters, and 440,241 reviews have 5 words or fewer. A few very long reviews create a strong right-skewed distribution.
7. **Product popularity is highly unbalanced.** 94,319 products share the reviews, 33,588 of them have a single review, and the most reviewed product has 12,027 reviews.
8. **Direct impact on the P05 design.** The findings support the use of Combiners, a careful look at skew (Partitioner decision), a minimum review threshold for TF-IDF and trends, explicit handling of missing months, and caution when interpreting stars as sentiment.

**Limits of this report.** The analysis is not exhaustive. The supplied results do not cover duplicates, `verified_purchase`, `helpful_vote`, titles, vocabulary, language, metadata or relationships between variables. These points are left for later stages.

---

## 12. Conclusion and transition to HDFS Bronze and data preparation

The exploration shows that the *Appliances* subset of Amazon Reviews 2023 is a suitable base for P05. It is large enough for a distributed approach, it has the fields required by the three MapReduce jobs, and it matches the size given in the specification. At the same time, the exploration reveals several points that will shape the next stages: a strong rating imbalance, many short reviews, a long-tailed distribution of reviews per product, sparse early years, and an incomplete last year.

**Reminder of the status of the data.** The original dataset was not modified, and no cleaning was applied. Duplicate detection and definitive data validation are reserved for the preparation stage.

### Next steps

| Step | Action | Linked P05 requirement |
|---|---|---|
| 1 | Archive the original `jsonl.gz` files in the **Bronze** zone of HDFS and write an ingestion manifest (source, size, checksums) | F01 |
| 2 | Verify the real unit of `timestamp` on concrete values and build a reliable `YYYY-MM` field | Section 6.2 |
| 3 | Validate records and count rejections by reason (invalid JSON, missing `parent_asin`, invalid rating, undecodable date, empty text) | F02, NF04 |
| 4 | Create a stable technical review key and apply a documented duplicate-detection rule | Section 6.4 |
| 5 | Define a deterministic selection of reviews (hash or versioned ID list) for the development lot and the validation lot, not "first lines only", and report the retention rate | Section 6.3 |
| 6 | Define and version the NLP rules (lowercase, tokenisation, stop words, numbers, negation, short words) and decide the policy for very short reviews | F03 |
| 7 | Produce the two Silver streams: tokenised texts (for MR1/MR2) and dated ratings (for MR3) | Section 6.4 |
| 8 | Compute the number of products that reach the minimum review threshold (default: 20) and store the value `N` in the preparation manifest | Section 8.2 |
| 9 | Keep `user_id` out of any output shown to the reader | NF05 |

The results of the next stage — the Bronze archive, the rejection log and the Silver data — will become the verified inputs of MR1, MR2 and MR3.

---

### Appendix — Source files used in this report

| File | Content |
|---|---|
| `dataset_summary.json` | Global summary (records, products, ratings, dates, text, data quality, analysis notes) |
| `schema_analysis.csv` | Field types and missing/null counts |
| `rating_distribution.csv` | Number and percentage of reviews by rating |
| `yearly_reviews.csv` | Reviews per year |
| `monthly_reviews.csv` | Reviews per month (242 rows) |
| `top_20_products.csv` | 20 most reviewed products |
| `reviews_per_product_distribution.csv` | Number of products by number of reviews (936 rows) |
| `text_statistics.csv` | Statistics on review length |
| Charts | Top 20 products, monthly review volume, rating distribution, text length distribution |

*Chart image files are referenced as `figures/top_20_products.png`, `figures/monthly_review_volume.png`, `figures/rating_distribution.png` and `figures/text_length_distribution.png`. Place the supplied charts in a `figures/` folder with these names (or update the paths) before exporting the report.*
