import gradio as gr
from agent.graph import create_graph

# Create the LangGraph agent
agent = create_graph()


def chat_interface(message, history):
    """
    The main chat interface function.
    """
    inputs = {"input": message, "messages": []}
    response = agent.invoke(inputs)
    return response["final_response"]


def main():
    """
    The main function to run the Gradio interface.
    """
    iface = gr.ChatInterface(
        fn=chat_interface,
        title="Medical Agent",
        description="A conversational agent for patients and doctors.",
    )
    iface.launch()


if __name__ == "__main__":
    main()
