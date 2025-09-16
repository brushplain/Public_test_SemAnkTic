

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
