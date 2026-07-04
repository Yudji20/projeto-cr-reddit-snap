
# %%
import pandas as pd
from pathlib import Path

ROOT = Path(r"C:\Users\Micro\Desktop\UFABC\CR\Projeto_CR")
RAW_PATH = ROOT / "data" / "raw" / "soc-redditHyperlinks-body.tsv"
OUT_DIR = ROOT / "data" / "processed"

OUT_DIR.mkdir(parents=True, exist_ok=True)

PROPERTY_COLUMNS = """
num_chars num_chars_no_spaces frac_alpha frac_digits frac_uppercase frac_whitespace frac_special
num_words num_unique_words num_long_words avg_word_length num_unique_stopwords frac_stopwords
num_sentences num_long_sentences avg_chars_per_sentence avg_words_per_sentence automated_readability_index
vader_positive vader_negative vader_compound
liwc_funct liwc_pronoun liwc_ppron liwc_i liwc_we liwc_you liwc_shehe liwc_they liwc_ipron
liwc_article liwc_verbs liwc_auxvb liwc_past liwc_present liwc_future liwc_adverbs liwc_prep
liwc_conj liwc_negate liwc_quant liwc_numbers liwc_swear liwc_social liwc_family liwc_friends
liwc_humans liwc_affect liwc_posemo liwc_negemo liwc_anx liwc_anger liwc_sad liwc_cogmech
liwc_insight liwc_cause liwc_discrep liwc_tentat liwc_certain liwc_inhib liwc_incl liwc_excl
liwc_percept liwc_see liwc_hear liwc_feel liwc_bio liwc_body liwc_health liwc_sexual liwc_ingest
liwc_relativ liwc_motion liwc_space liwc_time liwc_work liwc_achiev liwc_leisure liwc_home
liwc_money liwc_relig liwc_death liwc_assent liwc_dissent liwc_nonflu liwc_filler
""".split()
# %%

df = pd.read_csv(RAW_PATH, sep="\t")

# %%
df.head()

# %%

df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"])
df["LINK_SENTIMENT"] = df["LINK_SENTIMENT"].astype("int8")

properties = df["PROPERTIES"].str.split(",", expand=True)

if properties.shape[1] != len(PROPERTY_COLUMNS):
    raise ValueError(
        f"Esperava {len(PROPERTY_COLUMNS)} propriedades, "
        f"mas encontrei {properties.shape[1]}."
    )

properties.columns = PROPERTY_COLUMNS
properties = properties.astype("float32")

posts_expanded = pd.concat(
    [df.drop(columns=["PROPERTIES"]), properties],
    axis=1
)

posts_expanded.to_csv(
    OUT_DIR / "reddit_body_posts_expanded.csv",
    index=False
)

edges = (
    df.groupby(["SOURCE_SUBREDDIT", "TARGET_SUBREDDIT"])
      .agg(
          weight=("POST_ID", "count"),
          positive=("LINK_SENTIMENT", lambda x: (x == 1).sum()),
          negative=("LINK_SENTIMENT", lambda x: (x == -1).sum()),
          first_seen=("TIMESTAMP", "min"),
          last_seen=("TIMESTAMP", "max"),
      )
      .reset_index()
)

edges = edges.rename(columns={
    "SOURCE_SUBREDDIT": "Source",
    "TARGET_SUBREDDIT": "Target",
})

edges["Type"] = "Directed"

edges.to_csv(
    OUT_DIR / "reddit_body_edges_gephi.csv",
    index=False
)

print("Arquivos gerados:")
print(OUT_DIR / "reddit_body_posts_expanded.csv")
print(OUT_DIR / "reddit_body_edges_gephi.csv")
# %%
