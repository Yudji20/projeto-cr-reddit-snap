
# %%
import pandas as pd

path = "C:\\Users\\Micro\\Desktop\\UFABC\\CR\\Projeto_CR\\data\\raw\\soc-redditHyperlinks-title.tsv"

df = pd.read_csv(path, sep="\t")
# %%
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
    "TARGET_SUBREDDIT": "Target"
})

edges["Type"] = "Directed"
# %%
edges.to_csv("C:\\Users\\Micro\\Desktop\\UFABC\\CR\\Projeto_CR\\data\\processed\\reddit_title_edges_gephi.csv", index=False)
# %%
