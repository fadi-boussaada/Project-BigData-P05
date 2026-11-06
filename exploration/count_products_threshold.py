
import pandas as pd

file_path = "exploration/results/reviews_per_product_distribution.csv"

df = pd.read_csv(file_path)

# Count products with at least 20 reviews
products_at_least_20 = df.loc[
    df["reviews_per_product"] >= 20,
    "number_of_products"
].sum()

# Count products with fewer than 20 reviews
products_below_20 = df.loc[
    df["reviews_per_product"] < 20,
    "number_of_products"
].sum()

total_products = df["number_of_products"].sum()

percentage = (products_at_least_20 / total_products) * 100

print("Total products:", total_products)
print("Products with at least 20 reviews:", products_at_least_20)
print("Products with fewer than 20 reviews:", products_below_20)
print(f"Percentage with at least 20 reviews: {percentage:.2f}%")
