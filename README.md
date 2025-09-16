
# Who is the intended audience?
- Medical students using the Anking deck
- Radiology residents using the Ankore deck
- Anesthesia residents using the Ankisthesia deck


# What does this program does do?

- Help find relavent anki cards to study


# How does it search?

- it uses a embeds, reranking, and then deepseek-v3

# Where does it read data from?

 - An HDF5 file

# How is the HDF5 file made?

- by scrapping a SQL database to produce a CSV, then producing embeds for the CSV, then packaging everything in an HDF5 file that contains the card content, Numerical identifier (NID), and embeds

## Is the program that made the HDF5 file open source?
- Yes! But you need an API key to computer the embeds

# Which file is the entry point for this program?

`interface.py`

# What is the minimum I need to make this program work?

1. An HDF5 file
2. A Deepseek-v3 API key
3. A Cohere 3.5 rerank API key
4. A Nebious API key
