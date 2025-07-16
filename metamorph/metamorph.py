"""

MetaMorph.py

Main CLI runner script

Taking messy metadata—free-text columns, inconsistent formats, half-structured text, and turn it into structured,
machine-usable formats for downstream ML workflows. 
Think of it as a metadata refinery powered by LLM agents

"""


"""from pipeline.processor import MetaMorphProcessor

if __name__ == "__main__":
    print("🚀 Starting MetaMorph MVP pipeline...")
    processor = MetaMorphProcessor()
    processor.run()
"""


# metamorph.py
import pandas as pd
from llm_agent.column_labeler import label_column

def main():
    # Load sample input
    df = pd.DataFrame({
        "col_1": [
            "5 feet 10 inches", 
            "6ft", 
            "172cm"
        ]
    })

    # Pick column
    column_name = "col_1"
    column_data = df[column_name].tolist()

    # Call LLM agent stub
    labeled_output = label_column(column_name, column_data)

    # Display output
    print(f"📦 Processed Column: {column_name}")
    for i, item in enumerate(labeled_output):
        print(f"{i+1}. Input: {column_data[i]}")
        print(f"   Parsed: {item}\n")

if __name__ == "__main__":
    main()
