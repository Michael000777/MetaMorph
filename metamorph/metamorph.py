# metamorph.py

from llm_agent.metamorph_agent import initialize_metamorph_agent
from tabulate import tabulate

from dotenv import load_dotenv
load_dotenv()

def main():
    # Sample metadata column 
    column_data = [
        "5 ft 9 in",
        " 170cm ",
        "Six feet tall",
        "180 cm approx",
        "5ft-11in"
    ]

    agent = initialize_metamorph_agent()

    print("🔍 MetaMorph LLM Agent Results:\n")

    results = []
    for val in column_data:
        try:
            result = agent.invoke({"input": val})
            output = result.get("output", {})
            parsed_cm = output.get("parsed_height_cm", "N/A") if isinstance(output, dict) else str(output)
            results.append([val.strip(), parsed_cm])
        except Exception as e:
            results.append([val.strip(), f"Error: {str(e)}"])

    print(tabulate(results, headers=["Input", "Parsed Height (cm)"], tablefmt="grid"))

if __name__ == "__main__":
    main()
