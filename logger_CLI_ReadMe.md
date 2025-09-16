
 

# Q & A

## What is the default log level when the command line is used to send the query?
- INFO
- otherwise, the default level is also INFO





## What are the log levels?
- `DEBUG,INFO,WARNING,ERROR,CRITICAL`
    - from most to least detail

## Where are the logs stored?
- in this file: `flashcard_search.log`












# CLI commands

## For Help

```BASH
./Core.py --help
```

**This is what you should see:**
```BASH
Run one flashcard search end-to-end

options:
  -h, --help            show this help message and exit
  --config CONFIG       path to your config JSON
  --query QUERY         the text you want to search
  --json                output results as JSON
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set logging level
```



## To do a regular query

```BASH
./Core.py --query "cancer screening"
```
*(You need the quotation marks if the query is more than one word)*

## For JSON Output

```BASH
./Core.py --query "heart failure findings" --json
```

**Argument and code relationship**
```Python
if args.json:
    # Output as JSON for machine consumption
    print(json.dumps(result, indent=2))
```
```Python
 parser.add_argument(
        "--json",
        action="store_true",
        help="output results as JSON"
    )
```
## For Setting a log level 
- DEBUG= very detailed
  - the highiest log level

```BASH
./Core.py --query "cancer screening" --log-level DEBUG
```


# Argparse
- is related to the command line input
- is a mododule in Python's standard library

```python
import argparse
```

# CLI entry point
- Defines the command-line arguments using `argparse`

# What "results" mean in the code
- this is a **python dictionary**
  - you know this because of the `{}` symbols and the `Key: Value` pair
```Python
# Return a pure Python data structure without backward compatibility
result = {
                'query': query_text,
                'top_cards': top_cards,
                'llm_prompt': flash_output,
                'llm_response': chat_output,
                'extracted_code': code_output,
                'anki_status': anki_status
            }
```

# What the terminal seems to be prining

```Python
# Human-readable output
            print("\n=== FLASHCARD RESULTS ===\n")
            print(result["llm_prompt"])
            print("\n=== LLM RESPONSE ===\n")
            print(result["llm_response"])
            print(f"\n=== ANKI STATUS ===  {result['anki_status']}\n")
```

# print(result["llm_response"])
```Python
print(result["llm_response"])
```
- The square brackets `[ ]` in `result["llm_response"]` are Python's dictionary access 
notation.
- `result` is the name of the dictionary
---
## Example: Accessing Items
- You can access the items of a dictionary by referring to its key name, inside square brackets

```Python
thisdict = {
  "brand": "Ford",
  "model": "Mustang",
  "year": 1964
}
x = thisdict["model"]
```


# The `run()` method

The `run()` method returns a dictionary with the following keys:

- `query`: The original search query
- `top_cards`: List of the most relevant flashcards with similarity scores
- `llm_prompt`: The prompt sent to the LLM
- `llm_response`: The full response from the LLM
- `extracted_code`: Code blocks extracted from the LLM response
- `anki_status`: Current Anki application status
- `flash_output`: Human-readable flashcard results
- `chat_output`: Same as llm_response
- `code_output`: Same as extracted_code

## Command Line Usage

The program can also be used from the command line:

```bash
python Core.py --config search_essential_logic/config.json --query "Your search query" --json
```

