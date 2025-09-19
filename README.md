
# ⚠️ Note ⚠️

- I still to upload the program that makes the required `.h5` file that this program reads, since it does not directly read the Anki SQL file
- If you are urgently want to run this program, reach out to me at `marinefog3@gmail.com` and I give you the rest of the assets

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

# Screen shots

## SemAnkTic Program

<img width="563" height="537" alt="Screenshot 2025-09-19 at 9 03 03 AM" src="https://github.com/user-attachments/assets/43ffbefd-8be3-4c9a-97b0-546b9014b70b" />


<img width="568" height="927" alt="Screenshot 2025-09-19 at 9 06 04 AM" src="https://github.com/user-attachments/assets/165f9648-3320-4bad-ae6e-81d2c109652c" />

## Notes automatically open in Anki

<img width="1105" height="654" alt="Screenshot 2025-09-19 at 9 09 44 AM" src="https://github.com/user-attachments/assets/f9098795-c579-4dd0-9c8c-949dab363942" />


