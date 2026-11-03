from langgraph.graph import StateGraph , START , END , add_messages
from typing_extensions import TypedDict , Annotated , List 
from langchain_openai import ChatOpenAI 
from dotenv import load_dotenv
import os
from langchain_core.messages import BaseMessage , AIMessage , ToolMessage , HumanMessage , SystemMessage
from langgraph.prebuilt import ToolNode , InjectedState
from langchain_core.tools import tool
from langgraph.types import Command , interrupt 
from langgraph.checkpoint.memory import MemorySaver



load_dotenv()


AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")


class AgentState(TypedDict):
    messages : Annotated[ List[BaseMessage] ,  add_messages ]
    email_draft : str
    user_request : str
    filename : str


def call_llm() -> ChatOpenAI:
    try:

        return ChatOpenAI(

            api_key=AZURE_OPENAI_KEY,
            model=AZURE_OPENAI_DEPLOYMENT,
            base_url=AZURE_OPENAI_ENDPOINT
        )

    except Exception as e:
        print(" Error " , e)
        raise

@tool
def create_email(
    state: Annotated[AgentState, InjectedState]
) -> str:

    """This tool is used to create a new email."""

    return generate_email(state["user_request"])


@tool
def update_email(state: Annotated[AgentState , InjectedState] )  -> str :

    """ This tool is used to update an existing email """

    return revise_email(state["user_request"], state["email_draft"])


def generate_email(user_request: str) -> str:
    """Generate an email from a user request."""
    llm = call_llm()
    result = llm.invoke(
        [
            SystemMessage(
                content=(
                    "Create a professional email based on the following request. "
                    "Return only the email body.\n\n"
                    f"User request: {user_request}"
                )
            )
        ]
    )
    if not result.content:
        raise RuntimeError("The model returned an empty email.")
    return str(result.content)


def revise_email(user_request: str, email_draft: str) -> str:
    """Revise an email draft according to a user's request."""
    llm = call_llm()
    result = llm.invoke(
        [
            SystemMessage(
                content=(
                    "Update the email draft according to the user's request. "
                    "Return only the complete revised email body.\n\n"
                    f"User request: {user_request}\n"
                    f"Email draft:\n{email_draft}"
                )
            )
        ]
    )
    if not result.content:
        raise RuntimeError("The model returned an empty revised email.")
    return str(result.content)

# def agent(state  :AgentState) -> AgentState:

#     try:

#         llm = call_llm()

#         tools = [ create_email , update_email ]

#         messages = [
#             SystemMessage(content=f""" Analyse the user request completely , User Request :  { state['user_request'] } , 
#             select the tool depends upon the user request.

#             You have two tools to select

#             1. create_email - This tool is used to create a new email
#             2. update_email - This tool is used to update an existing email
             
#                """)
#         ]

#         llm = llm.bind_tools(tools=tools)

#         result = llm.invoke(messages)

#         # messages.append(result)

#         print( " Selectd Tool : " , result.tool_calls )

#         # state['messages'].append(messages)

#         if result.tool_calls:
#             call_tool = ToolNode([create_email , update_email])
#             tool_call = call_tool.invoke({
#                 **state,
#                 "messages": [result]
#             })

#             print( " Tool Result : " , tool_call )

#         # return {
#         #     'messages': messages
#         # }

#         # state['messages'].append(tool_call)

#         return state


#     except Exception as e:
#         print(  "Error " , e  )


def agent(state: AgentState) -> AgentState:

    try:

        llm = call_llm()

        tools = [create_email, update_email]

        while True :
            system_message = SystemMessage(
                content=f"""
                Analyse the user request completely.

                User Request: {state['user_request']} and Email Draft : {state.get('email_draft', 'Not created yet')}

                if the user request is more complex to understand check the email draft .

                Select the appropriate tool:

                1. create_email - Create a new email.
                2. update_email - Update an existing email.
                """
            )

            messages = [system_message] + state.get("messages", [])

            llm = llm.bind_tools(tools=tools)

            result = llm.invoke(messages)

            print("Selected Tool:", result.tool_calls)

            if result.tool_calls:
                break

        if result.tool_calls:

            call_tool = ToolNode(tools)

            tool_result = call_tool.invoke({
                **state,
                "messages": [result]
            })

            print("Tool Result:", tool_result)

            # Extract the generated email
            email = tool_result["messages"][-1].content

            return {
                "messages": [result] + tool_result["messages"],
                "email_draft": email
            }

        return {
            "messages": [result]
        }

    except Exception as e:

        print("Agent Error:", e)
        raise



def save_file( state : AgentState ) -> AgentState:
    try:
        with open(f""" {state['filename']} """,'w+') as f:
            f.write(state['email_draft'])

    except Exception as e:
        print( " Error " , e )
        raise

def start_message(state : AgentState) -> AgentState:
    try:

        while True:


            if len(state['messages']) == 0:     
                user_request = input( " Enter what you want to create as an email :  " )
            else:
                user_request = input( " Enter what you want to update in email :  " )

            if user_request.strip().lower():
                state['user_request'] = user_request
                break

            continue

        return state

    except Exception as e:
        print( " Error " , e )
        raise

def get_confirmation( state : AgentState ) -> str:
    try:

        question = input( " Do you want to edit or update the email?  /n OPTIONS : [ YES , yes , s ] "  )

        if question.lower().strip() in ['yes' , 's']:
            return "start_message"
        return "get_email_name"


    except Exception as e:
        print(" Error " , e)

    
def get_email_name( state : AgentState ) -> AgentState:

    try:

        print( " Generating Email Name .... !!!  " )

        llm = call_llm()

        PROMPT = [SystemMessage(content=f""" Analyse the email : {state['email_draft']} , create a proper valid name based on the email content  don't add any extension like only generate the email name """)]

        result = llm.invoke(
            PROMPT
        )

        print(result.content)

        filename = result.content

        if filename not in ['.txt']:
            filename = filename+".txt"

        return {
            'filename' : filename ,
            'messages' : result
        }
        

    except Exception as e:
        print( " Error " , e )
        raise

# def human_in_loop( state : AgentState ) -> Command:
#     # try:

#             confirmation = interrupt({
#                 "instruction": "Do you want to edit or update the email?",
#                 "options": ["yes", "no"]
#             })


#             result = confirmation.get("confirmation" , "")

#             if (result.lower() == 'yes'):
#                 return Command(goto="start_message")

#             else:
#                 return Command(goto="save_file")

#     # except Exception as e:
#     #         print( " Error " , e )
#     #         raise
