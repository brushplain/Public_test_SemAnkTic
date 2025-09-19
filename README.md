
# ⚠️ Note ⚠️

- I still need to upload the program that makes the required `.h5` file that this program reads, since it does not directly read the Anki SQL file
- If you are urgently want to run this program, reach out to me at `marinefog3@gmail.com` and I can give you the rest of the assets



# Screen shots

## SemAnkTic Program





<img width="520" height="320" alt="Screenshot 2025-09-19 at 9 30 30 AM" src="https://github.com/user-attachments/assets/8660165e-2998-4b5d-883c-1c038cae0feb" />


<img width="761" height="773" alt="Screenshot 2025-09-19 at 9 29 16 AM" src="https://github.com/user-attachments/assets/7e68aa90-d15e-448e-9cd5-d8c21121e1d0" />

## Results automatically open in Anki 

- Needs the  `Sort on NID` and `AnkiConnect` addon to automatically open and populate Anki in the order displayed from the SemAnkTic program


<img width="1299" height="736" alt="Screenshot 2025-09-19 at 9 34 45 AM" src="https://github.com/user-attachments/assets/dba9dda0-92e2-407f-9f43-75dba36e257d" />

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
- Yes! But you need an API key to compute the embeds

# Which file is the entry point for this program?

`interface.py`

# What is the minimum I need to make this program work?

1. An HDF5 file
2. Deepseek-v3 API key
3. Cohere 3.5 rerank API key
4. Nebious API key



