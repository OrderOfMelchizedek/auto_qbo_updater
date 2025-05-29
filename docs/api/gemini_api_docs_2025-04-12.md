**1. URL: https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/send-chat-prompts-gemini**

```markdown
[Skip to main content](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/send-chat-prompts-gemini#main-content)

[![Google Cloud](https://www.gstatic.com/devrel-devsite/prod/vd31e3ed8994e05c7f2cd0cf68a402ca7902bb92b6ec0977d7ef2a1c699fae3f9/cloud/images/cloud-logo.svg)](https://cloud.google.com/)

`/`

- English
- Deutsch
- Español – América Latina
- Français
- Indonesia
- Italiano
- Português – Brasil
- 中文 – 简体
- 日本語
- 한국어

[Console](https://console.cloud.google.com/)Sign in

- [Generative AI on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/overview)

[Contact Us](https://cloud.google.com/contact) [Start free](https://console.cloud.google.com/freetrial)

- [Home](https://cloud.google.com/)
- [Generative AI on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/overview)
- [Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/overview)

 Send feedback

# Text generation       Stay organized with collections     Save and categorize content based on your preferences.

This page shows you how to send chat prompts to a Gemini model by using
the Google Cloud console, REST API, and supported SDKs.

To learn how to add images and other media to your request, see
[Image understanding](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/image-understanding).

For a list of languages supported by Gemini, see
[Language support](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/models#languages-gemini).

* * *

To explore
the generative AI models and APIs that are available on Vertex AI, go to
Model Garden in the Google Cloud console.

[Go to Model Garden](https://console.cloud.google.com/vertex-ai/model-garden)

* * *

If you're looking for a way to use Gemini directly from your mobile and
web apps, see the
[Vertex AI in Firebase SDKs](https://firebase.google.com/docs/vertex-ai) for
Android, Swift, web, and Flutter apps.

## Generate text

For testing and iterating on chat prompts, we recommend using the
Google Cloud console. To send prompts programmatically to the model, you can use the
REST API, Google Gen AI SDK, Vertex AI SDK for Python, or one of the other supported libraries and
SDKs.

You can use system instructions to steer the behavior of the model based on a
specific need or use case. For example, you can define a persona or role for a
chatbot that responds to customer service requests. For more information, see
the
[system instructions code samples](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/system-instructions#code_samples).

### Gemini 2.0

You can use the [Google Gen AI SDK](https://cloud.google.com/vertex-ai/generative-ai/docs/gemini-v2#google-gen) to send requests if
you're using
[Gemini 2.0 Flash](https://cloud.google.com/vertex-ai/generative-ai/docs/gemini-v2).

### Streaming and non-streaming responses

You can choose whether the model generates _streaming_ responses or
_non-streaming_ responses. For streaming responses, you receive each response
as soon as its output token is generated. For non-streaming responses, you receive
all responses after all of the output tokens are generated.

#### Streaming

### Gen AI SDK for Python

#### Install

```
pip install --upgrade google-genai
```

To learn more, see the
[SDK reference documentation](https://googleapis.github.io/python-genai/).

Set environment variables to use the Gen AI SDK with Vertex AI:

```
# Replace the `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` values
# with appropriate values for your project.
export GOOGLE_CLOUD_PROJECT=GOOGLE_CLOUD_PROJECT
export GOOGLE_CLOUD_LOCATION=us-central1
export GOOGLE_GENAI_USE_VERTEXAI=True
```

```
from google import genai
from google.genai.types import HttpOptions

client = genai.Client(http_options=HttpOptions(api_version=\"v1\"))
chat_session = client.chats.create(model=\"gemini-2.0-flash-001\")
response_text = \"\"

for chunk in chat_session.send_message_stream(\"Why is the sky blue?\"):
    print(chunk.text, end=\"\")
    response_text += chunk.text
# Example response:
# The
#  sky appears blue due to a phenomenon called **Rayleigh scattering**. Here's
#  a breakdown of why:
# ...
```

#### Non-Streaming

### Gen AI SDK for Python

#### Install

```
pip install --upgrade google-genai
```

To learn more, see the
[SDK reference documentation](https://googleapis.github.io/python-genai/).

Set environment variables to use the Gen AI SDK with Vertex AI:

```
# Replace the `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` values
# with appropriate values for your project.
export GOOGLE_CLOUD_PROJECT=GOOGLE_CLOUD_PROJECT
export GOOGLE_CLOUD_LOCATION=us-central1
export GOOGLE_GENAI_USE_VERTEXAI=True```

```
from google import genai
from google.genai.types import HttpOptions, ModelContent, Part, UserContent

client = genai.Client(http_options=HttpOptions(api_version=\"v1\"))
chat_session = client.chats.create(
    model=\"gemini-2.0-flash-001\",
    history=[\\
        UserContent(parts=[Part(text=\"Hello\")]),\\
        ModelContent(\\
            parts=[Part(text=\"Great to meet you. What would you like to know?\")],\\
        ),\\
    ],
)
response = chat_session.send_message(\"Tell me a story.\")
print(response.text)
# Example response:
# Okay, here's a story for you:
# ...
```

## What's next

- Learn how to send multimodal prompt requests:

  - [Image understanding](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/image-understanding)
  - [Video understanding](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/video-understanding)
  - [Audio understanding](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/audio-understanding)
  - [Document understanding](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding)
- Learn about [responsible AI best practices and Vertex AI's safety filters](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/responsible-ai).

 Send feedback

Except as otherwise noted, the content of this page is licensed under the [Creative Commons Attribution 4.0 License](https://creativecommons.org/licenses/by/4.0/), and code samples are licensed under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0). For details, see the [Google Developers Site Policies](https://developers.google.com/site-policies). Java is a registered trademark of Oracle and/or its affiliates.

Last updated 2025-04-12 UTC.
```

**2. URL: https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling**

```markdown
[Skip to main content](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling#main-content)

[![Google Cloud](https://www.gstatic.com/devrel-devsite/prod/vd31e3ed8994e05c7f2cd0cf68a402ca7902bb92b6ec0977d7ef2a1c699fae3f9/cloud/images/cloud-logo.svg)](https://cloud.google.com/)

`/`

- English
- Deutsch
- Español – América Latina
- Français
- Indonesia
- Italiano
- Português – Brasil
- 中文 – 简体
- 日本語
- 한국어

[Console](https://console.cloud.google.com/)Sign in

- [Generative AI on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/overview)

[Contact Us](https://cloud.google.com/contact) [Start free](https://console.cloud.google.com/freetrial)

- [Home](https://cloud.google.com/)
- [Generative AI on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/overview)
- [Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/overview)

 Send feedback

# Introduction to function calling       Stay organized with collections     Save and categorize content based on your preferences.

Large Language Models (LLMs) are powerful at solving many types of problems.
However, they are constrained by the following limitations:

- They are frozen after training, leading to stale knowledge.
- They can't query or modify external data.

Function calling can address these shortcomings. Function calling is sometimes
referred to as _tool use_ because it allows the model to use external tools such
as APIs and functions.

When submitting a prompt to the LLM, you also
provide the model with a set of tools that it can use to respond to the user's prompt. For
example, you could provide a function `get_weather` that takes a location
parameter and returns information about the weather conditions at that location.

While processing a prompt, the model can choose to delegate certain
data processing tasks to the functions that you identify. The model does not
call the functions directly. Instead, the model provides structured data output
that includes the function to call and parameter values to use. For example, for
a prompt `What is the weather like in Boston?`, the model can delegate processing
to the `get_weather` function and provide the location parameter value `Boston, MA`.

You can use the structured output from the model to invoke external APIs. For
example, you could connect to a weather service API, provide the location
`Boston, MA`, and receive information about temperature, cloud cover, and wind
conditions.

You can then provide the API output back to the model, allowing it to complete
its response to the prompt. For the weather example, the model may provide the
following response: `It is currently 38 degrees Fahrenheit in Boston, MA with partly cloudy skies.`

![Function Calling Interaction](https://cloud.google.com/static/vertex-ai/generative-ai/docs/multimodal/images/function-calling.png)

## Supported models

The following models provide support for function calling:

- [Vertex AI Model Optimizer](https://console.cloud.google.com/vertex-ai/publishers/google/model-garden/model-optimizer-exp-04-09)
- [Gemini 2.5 Pro](https://console.cloud.google.com/vertex-ai/publishers/google/model-garden/gemini-2.5-pro-exp-03-25)
- [Gemini 2.0 Flash](https://console.cloud.google.com/vertex-ai/publishers/google/model-garden/gemini-2.0-flash-001)
- [Gemini 2.0 Flash-Lite](https://console.cloud.google.com/vertex-ai/publishers/google/model-garden/gemini-2.0-flash-lite-001)

## Use cases of function calling

You can use function calling for the following tasks:

| Use Case | Example description | Example link |
| --- | --- | --- |
| Integrate with external APIs | Get weather information using a meteorological API | [Notebook tutorial](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/function-calling/intro_function_calling.ipynb) |
| Convert addresses to latitude/longitude coordinates | [Notebook tutorial](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/function-calling/intro_function_calling.ipynb) |
| Convert currencies using a currency exchange API | [Codelab](https://codelabs.developers.google.com/codelabs/gemini-function-calling) |
| Build advanced chatbots | Answer customer questions about products and services | [Notebook tutorial](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/function-calling/intro_function_calling.ipynb) |
| Create an assistant to answer financial and news questions about companies | [Notebook tutorial](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/function-calling/use_case_company_news_and_insights.ipynb) |
| Structure and control function calls | Extract structured entities from raw log data | [Notebook tutorial](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/function-calling/intro_function_calling.ipynb) |
| Extract single or multiple parameters from user input | [Notebook tutorial](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/function-calling/function_calling_data_structures.ipynb) |
| Handle lists and nested data structures in function calls | [Notebook tutorial](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/function-calling/function_calling_data_structures.ipynb) |
| Handle function calling behavior | Handle parallel function calls and responses | [Notebook tutorial](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/function-calling/parallel_function_calling.ipynb) |
| Manage when and which functions the model can call | [Notebook tutorial](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/function-calling/forced_function_calling.ipynb) |
| Query databases with natural language | Convert natural language questions into SQL queries for BigQuery | [Sample app](https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/function-calling/sql-talk-app) |
| Multimodal function calling | Use images, videos, audio, and PDFs as input to trigger function calls | [Notebook tutorial](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/function-calling/multimodal_function_calling.ipynb) |

Here are some more use cases:

- **Interpret voice commands**: Create functions that correspond with
in-vehicle tasks. For example, you can create functions that turn on the
radio or activate the air conditioning. Send audio files of the user's voice
commands to the model, and ask the model to convert the audio into text and
identify the function that the user wants to call.

- **Automate workflows based on environmental triggers**: Create functions to
represent processes that can be automated. Provide the model with data from
environmental sensors and ask it to parse and process the data to determine
whether one or more of the workflows should be activated. For example, a
model could process temperature data in a warehouse and choose to activate a
sprinkler function.

- **Automate the assignment of support tickets**: Provide the model with
support tickets, logs, and context-aware rules. Ask the model to process all
of this information to determine who the ticket should be assigned to. Call
a function to assign the ticket to the person suggested by the model.

- **Retrieve information from a knowledge base**: Create functions that
retrieve academic articles on a given subject and summarize them. Enable the
model to answer questions about academic subjects and provide citations for
its answers.

## How to create a function calling application

To enable a user to interface with the model and use function calling, you must
create code that performs the following tasks:

1. [Set up your environment](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling#initialize-model).
2. [Define and describe a set of available functions](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling#function-declarations)
using _function declarations_.
3. [Submit a user's prompt and the function declarations to the model](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling#submit-prompt).
4. [Invoke a function](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling#invoke-api) using the structured data output from the model.
5. [Provide the function output to the model](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling#submit-api-output).

You can create an application that manages all of these tasks. This application
can be a text chatbot, a voice agent, an automated workflow, or any other program.

You can use function calling to generate a single text response or to support
a chat session. Ad hoc text responses are useful for specific business tasks,
including code generation. Chat sessions are useful in freeform, conversational
scenarios, where a user is likely to ask follow-up questions.

If you use function calling to generate a single response, you must provide the
model with the full context of the interaction. On the other hand, if you use
function calling in the context of a chat session, the session stores the
context for you and includes it in every model request. In both cases,
Vertex AI stores the history of the interaction on the client side.

This guide demonstrates how you can use function calling to generate a single
text response. For an end-to-end sample, see [Text examples](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling#text-samples).
To learn how to use function calling to support a chat session, see
[Chat examples](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling#chat-samples).

### Step 1: Set up your environment

Import the required modules and initialize the model:

### Python

```
import vertexai
from vertexai.generative_models import (
    Content,
    FunctionDeclaration,
    GenerationConfig,
    GenerativeModel,
    Part,
    Tool,
)

# Initialize Vertex AI
# TODO(developer): Update and un-comment below lines
# PROJECT_ID = 'your-project-id'
vertexai.init(project=PROJECT_ID, location=\"us-central1\")

# Initialize Gemini model
model = GenerativeModel(model_name=\"gemini-2.0-flash\")

```

### Step 2: Declare a set of functions

Declare a [`Tool`](https://cloud.google.com/vertex-ai/generative-ai/docs/reference/python/latest/vertexai.generative_models.Tool) that contains up to 128 [`FunctionDeclarations`](https://cloud.google.com/vertex-ai/generative-ai/docs/reference/python/latest/vertexai.generative_models.FunctionDeclaration). You will later pass this tool to the model when submitting the prompt. The model can use the functions in the tool to process the prompt. At most one tool can be provided with the request.

You must provide function declarations in a schema format that's compatible with the [OpenAPI schema](https://spec.openapis.org/oas/v3.0.3#schema). Vertex AI offers limited support of the OpenAPI schema. The following attributes are supported from the OpenAPI schema: `type`, `nullable`, `required`, `format`, `description`, `properties`, `items`, `enum`, `anyOf`. Remaining attributes are not supported. For best practices related to the function declarations, including tips for names and descriptions, see [Best practices](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling#best-practices).

If you use the REST API, specify the schema using JSON. If you use the
Vertex AI SDK for Python, you can specify the schema either manually using a Python dictionary or automatically with the `from_func` helper function.

### JSON

```
{
  \"contents\": ...,
  \"tools\": [\\
    {\\
      \"function_declarations\": [\\
        {\\
          \"name\": \"find_movies\",\\
          \"description\": \"find movie titles currently playing in theaters based on any description, genre, title words, etc.\",\\
          \"parameters\": {\\
            \"type\": \"object\",\\
            \"properties\": {\\
              \"location\": {\\
                \"type\": \"string\",\\
                \"description\": \"The city and state, e.g. San Francisco, CA or a zip code e.g. 95616\"\\
              },\\
              \"description\": {\\
                \"type\": \"string\",\\
                \"description\": \"Any kind of description including category or genre, title words, attributes, etc.\"\
              }\\
            },\\
            \"required\": [\\
              \"description\"\\
            ]\\
          }\\
        },\\
        {\\
          \"name\": \"find_theaters\",\\
          \"description\": \"find theaters based on location and optionally movie title which are is currently playing in theaters\",\\
          \"parameters\": {\\
            \"type\": \"object\",\\
            \"properties\": {\\
              \"location\": {\\
                \"type\": \"string\",\\
                \"description\": \"The city and state, e.g. San Francisco, CA or a zip code e.g. 95616\"\\
              },\\
              \"movie\": {\\
                \"type\": \"string\",\\
                \"description\": \"Any movie title\"\\
              }\\
            },\\
            \"required\": [\\
              \"location\"\\
            ]\\
          }\\
        },\\
        {\\
          \"name\": \"get_showtimes\",\\
          \"description\": \"Find the start times for movies playing in a specific theater\",\\
          \"parameters\": {\\
            \"type\": \"object\",\\
            \"properties\": {\\
              \"location\": {\\
                \"type\": \"string\",\\
                \"description\": \"The city and state, e.g. San Francisco, CA or a zip code e.g. 95616\"\\
              },\\
              \"movie\": {\\
                \"type\": \"string\",\\
                \"description\": \"Any movie title\"\\
              },\\
              \"theater\": {\\
                \"type\": \"string\",\\
                \"description\": \"Name of the theater\"\\
              },\\
              \"date\": {\\
                \"type\": \"string\",\\
                \"description\": \"Date for requested showtime\"\\
              }\\
            },\\
            \"required\": [\\
              \"location\",\\
              \"movie\",\\
              \"theater\",\\
              \"date\"\\
            ]\\
          }\\
        }\\
      ]\\
    }\\
  ]
}

```

### Python dictionary

The following function declaration takes a single `string` parameter:

```
function_name = \"get_current_weather\"
get_current_weather_func = FunctionDeclaration(
    name=function_name,
    description=\"Get the current weather in a given location\",
    # Function parameters are specified in JSON schema format
    parameters={
        \"type\": \"object\",
        \"properties\": {
            \"location\": {\"type\": \"string\", \"description\": \"The city name of the location for which to get the weather.\"}
        },
    },
)

```

The following function declaration takes both object and array parameters:

```
extract_sale_records_func = FunctionDeclaration(
  name=\"extract_sale_records\",
  description=\"Extract sale records from a document.\",
  parameters={
      \"type\": \"object\",
      \"properties\": {
          \"records\": {
              \"type\": \"array\",
              \"description\": \"A list of sale records\",
              \"items\": {
                  \"description\": \"Data for a sale record\",
                  \"type\": \"object\",
                  \"properties\": {
                      \"id\": {\"type\": \"integer\", \"description\": \"The unique id of the sale.\"},
                      \"date\": {\"type\": \"string\", \"description\": \"Date of the sale, in the format of MMDDYY, e.g., 031023\"},
                      \"total_amount\": {\"type\": \"number\", \"description\": \"The total amount of the sale.\"},
                      \"customer_name\": {\"type\": \"string\", \"description\": \"The name of the customer, including first name and last name.\"},
                      \"customer_contact\": {\"type\": \"string\", \"description\": \"The phone number of the customer, e.g., 650-123-4567.\"},
                  },
                  \"required\": [\"id\", \"date\", \"total_amount\"],
              },
          },
      },
      \"required\": [\"records\"],
  },
)

```

### Python from function

The following code sample declares a function that multiplies an array of numbers and uses `from_func` to generate the `FunctionDeclaration` schema.

```

from typing import List

# Define a function. Could be a local function or you can import the requests library to call an API
def multiply_numbers(numbers: List[int]) -> int:
  \"\"\"
  Calculates the product of all numbers in an array.

  Args:
      numbers: An array of numbers to be multiplied.

  Returns:
      The product of all the numbers. If the array is empty, returns 1.
  \"\"\"

  if not numbers:  # Handle empty array
      return 1

  product = 1
  for num in numbers:
      product *= num

  return product

multiply_number_func = FunctionDeclaration.from_func(multiply_numbers)

'''
multiply_number_func contains the following schema:

{'name': 'multiply_numbers',
'description': 'Calculates the product of all numbers in an array.',
'parameters': {'properties': {'numbers': {'items': {'type': 'INTEGER'},
    'description': 'list of numbers',
    'title': 'Numbers',
    'type': 'ARRAY'}},
  'required': ['numbers'],
  'description': 'Calculates the product of all numbers in an array.',
  'title': 'multiply_numbers',
  'property_ordering': ['numbers'],
  'type': 'OBJECT'}}
'''

```

### Step 3: Submit the prompt and function declarations to the model

When the user provides a prompt, the application must provide the model with the
user prompt and the _function declarations_. To configure how the model
generates results, the application can provide the model with a
_generation configuration_. To configure how the model uses the function declarations,
the application can provide the model with a _tool configuration_.

#### Define the user prompt

The following is an example of a user prompt: \"What is the weather like in Boston?\"

The following is an example of how you can define the user prompt:

### Python

```
# Define the user's prompt in a Content object that we can reuse in model calls
user_prompt_content = Content(
    role=\"user\",
    parts=[\\
        Part.from_text(\"What is the weather like in Boston?\"),\\
    ],
)

```

For best practices related to the user prompt, see
[Best practices - User prompt](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling#prompt-bp).

#### Generation configuration

The model can generate different results for different parameter values. The
temperature parameter controls the degree of randomness in this generation.
Lower temperatures are good for functions that require deterministic parameter
values, while higher temperatures are good for functions with parameters that
accept more diverse or creative parameter values. A temperature of `0` is
deterministic. In this case, responses for a given prompt are mostly
deterministic, but a small amount of variation is still possible. To learn
more, see [Gemini API](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/gemini).

To set this parameter, submit a generation configuration ( `generation_config`)
along with the prompt and the function declarations. You can update the
`temperature` parameter during a chat conversation using the Vertex AI
API and an updated `generation_config`. For an example of setting the
`temperature` parameter, see
[How to submit the prompt and the function declarations](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling#how_to_submit_the_prompt_and_the_function_declarations).

For best practices related to the generation configuration, see
[Best practices - Generation configuration](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling#generation-config-bp).

#### Tool configuration

You can place some constraints on how the model should use the function
declarations that you provide it with. For example, instead of allowing the
model to choose between a natural language response and a function call, you can
force it to only predict function calls. This is known as \"forced function
calling\". You can also choose to provide the model with a full set of
function declarations, but restrict its responses to a subset of these
functions.

To place these constraints, submit a tool configuration ( `tool_config`) along
with the prompt and the function declarations. In the configuration, you can
specify one of the following modes:

| Mode | Description |
| --- | --- |
| `AUTO` | The default model behavior. The model decides whether to predict function calls or a natural language response. |
| `ANY` | The model is constrained to always predict a function call. If `allowed_function_names` is not provided, the model picks from all of the available function declarations. If `allowed_function_names` is provided, the model picks from the set of allowed functions. |
| `NONE` | The model must not predict function calls. This behaviour is equivalent to a model request without any associated function declarations. |

For a list of models that support the `ANY` mode (\"forced function calling\"),
see [supported models](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling#supported_models).

To learn more, see [Function Calling API](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/function-calling).

#### How to submit the prompt and the function declarations

The following is an example of how can you submit the prompt and the function
declarations to the model, and constrain the model to predict only
`get_current_weather` function calls.

### Python

```# Define a tool that includes some of the functions that we declared earlier
tool = Tool(
    function_declarations=[get_current_weather_func, extract_sale_records_func, multiply_number_func],
)

# Send the prompt and instruct the model to generate content using the Tool object that you just created
response = model.generate_content(
    user_prompt_content,
    generation_config=GenerationConfig(temperature=0),
    tools=[tool],
    tool_config=ToolConfig(
        function_calling_config=ToolConfig.FunctionCallingConfig(
            # ANY mode forces the model to predict only function calls
            mode=ToolConfig.FunctionCallingConfig.Mode.ANY,
            # Allowed function calls to predict when the mode is ANY. If empty, any  of
            # the provided function calls will be predicted.
            allowed_function_names=[\"get_current_weather\"],
        )
    )
)

```

If the model determines that it needs the output of a particular function, the
response that the application receives from the model contains the function name
and the parameter values that the function should be called with.

The following is an example of a model response to the user prompt \"What is the weather like in Boston?\". The model proposes calling
the `get_current_weather` function with the parameter `Boston, MA`.

```
candidates {
  content {
    role: \"model\"
    parts {
      function_call {
        name: \"get_current_weather\"
        args {
          fields {
            key: \"location\"
            value {
              string_value: \"Boston, MA\"
            }
          }
        }
      }
    }
  }
  ...
}```

For prompts such as \"Get weather details in New Delhi and San Francisco?\",
the model may propose several parallel function calls. To
learn more, see [Parallel function calling example](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling#parallel-samples).

### Step 4: Invoke an external API

If the application receives a function name and parameter values from the
model, the application must connect to an external API and call the function.

The following example uses synthetic data to simulate a response payload from
an external API:

### Python

```
# Check the function name that the model responded with, and make an API call to an external system
if (response.candidates[0].function_calls[0].name == \"get_current_weather\"):
    # Extract the arguments to use in your API call
    location = response.candidates[0].function_calls[0].args[\"location\"]

    # Here you can use your preferred method to make an API request to fetch the current weather, for example:
    # api_response = requests.post(weather_api_url, data={\"location\": location})

    # In this example, we'll use synthetic data to simulate a response payload from an external API
    api_response = \"\"\"{\"location\": \"Boston, MA\", \"temperature\": 38, \"description\": \"Partly Cloudy\",
                    \"icon\": \"partly-cloudy\", \"humidity\": 65, \"wind\": {\"speed\": 10, \"direction\": \"NW\"}}"""

```

For best practices related to API invocation, see [Best practices - API invocation](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling#invoke-api-bp).

### Step 5: Provide the function's output to the model

After an application receives a response from an external API, the application must
provide this response to the model. The following is an example of how you
can do this using Python:

### Python

```
response = model.generate_content(
    [\\
        user_prompt_content,  # User prompt\\
        response.candidates[0].content,  # Function call response\\
        Content(\\
            parts=[\\
                Part.from_function_response(\\
                    name=\"get_current_weather\",\\
                    response={\\
                        \"content\": api_response,  # Return the API response to Gemini\\
                    },\\
                )\\
            ],\\
        ),\\
    ],
    tools=[weather_tool],
)
# Get the model summary response
summary = response.text

```

If the model had proposed several parallel function calls, the application must
provide all of the responses back to the model. To learn more, see
[Parallel function calling example](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling#parallel-samples).

The model may determine that the
output of another function is necessary for responding to the prompt. In this case,
the response that the application receives from the model contains another
function name and another set of parameter values.

If the model determines that the API response is sufficient for responding to
the user's prompt, it creates a natural language response and returns it to the
application. In this case, the application must pass the response back to the
user. The following is an example of a response:

```
It is currently 38 degrees Fahrenheit in Boston, MA with partly cloudy skies. The humidity is 65% and the wind is blowing at 10 mph from the northwest.

```

## Examples of function calling

### Text examples

You can use function calling to generate a single text response. Ad hoc text
responses are useful for specific business tasks, including code generation.

If you use function calling to generate a single response, you must provide the
model with the full context of the interaction. Vertex AI stores
the history of the interaction on the client side.

### Python

This example demonstrates a text scenario with one function and one
prompt. It uses the `GenerativeModel` class and its methods. For more
information about using the Vertex AI SDK for Python with Gemini multimodal
models, see
[Introduction to multimodal classes in the Vertex AI SDK for Python](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/sdk-for-gemini/gemini-sdk-overview).

### Gen AI SDK for Python

#### Install

```
pip install --upgrade google-genai
```

To learn more, see the
[SDK reference documentation](https://googleapis.github.io/python-genai/).

Set environment variables to use the Gen AI SDK with Vertex AI:

```
# Replace the `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` values
# with appropriate values for your project.
export GOOGLE_CLOUD_PROJECT=GOOGLE_CLOUD_PROJECT
export GOOGLE_CLOUD_LOCATION=us-central1
export GOOGLE_GENAI_USE_VERTEXAI=True```

```
from google import genai
from google.genai.types import (
    FunctionDeclaration,
    GenerateContentConfig,
    HttpOptions,
    Tool,
)

client = genai.Client(http_options=HttpOptions(api_version=\"v1\"))
model_id = \"gemini-2.0-flash-001\"

get_album_sales = FunctionDeclaration(
    name=\"get_album_sales\",
    description=\"Gets the number of albums sold\",
    # Function parameters are specified in JSON schema format
    parameters={
        \"type\": \"OBJECT\",
        \"properties\": {
            \"albums\": {
                \"type\": \"ARRAY\",
                \"description\": \"List of albums\",
                \"items\": {
                    \"description\": \"Album and its sales\",
                    \"type\": \"OBJECT\",
                    \"properties\": {
                        \"album_name\": {
                            \"type\": \"STRING\",
                            \"description\": \"Name of the music album\",
                        },
                        \"copies_sold\": {
                            \"type\": \"INTEGER\",
                            \"description\": \"Number of copies sold\",
                        },
                    },
                },
            },
        },
    },
)

sales_tool = Tool(
    function_declarations=[get_album_sales],
)

response = client.models.generate_content(
    model=model_id,
    contents='At Stellar Sounds, a music label, 2024 was a rollercoaster. \"Echoes of the Night,\" a debut synth-pop album, '
    'surprisingly sold 350,000 copies, while veteran rock band \"Crimson Tide\\\'s\" latest, \"Reckless Hearts,\" '
    'lagged at 120,000. Their up-and-coming indie artist, \"Luna Bloom\\\'s\" EP, \"Whispers of Dawn,\" '
    'secured 75,000 sales. The biggest disappointment was the highly-anticipated rap album \"Street Symphony\" '
    "only reaching 100,000 units. Overall, Stellar Sounds moved over 645,000 units this year, revealing unexpected \"
    \"trends in music consumption.\",
    config=GenerateContentConfig(
        tools=[sales_tool],
        temperature=0,
    ),
)

print(response.function_calls[0])
# Example response:
# [FunctionCall(\\\
#     id=None,\\\\
#     name=\"get_album_sales\",\\\\
#     args={\\\
#         \"albums\": [\\\\
#             {\"album_name\": \"Echoes of the Night\", \"copies_sold\": 350000},\\\\
#             {\"copies_sold\": 120000, \"album_name\": \"Reckless Hearts\"},\\\\
#             {\"copies_sold\": 75000, \"album_name\": \"Whispers of Dawn\"},\\\\
#             {\"copies_sold\": 100000, \"album_name\": \"Street Symphony\"},\\\\
#         ]\\
#     },\\\\
# )]
```

### Node.js

This example demonstrates a text scenario with one function and one
prompt.

### Node.js

Before trying this sample, follow the Node.js setup instructions in the
[Vertex AI quickstart using\\
client libraries](https://cloud.google.com/vertex-ai/docs/start/client-libraries).

For more information, see the
[Vertex AI Node.js API\\
reference documentation](https://cloud.google.com/nodejs/docs/reference/aiplatform/latest).

To authenticate to Vertex AI, set up Application Default Credentials.
For more information, see

[Set up authentication for a local development environment](https://cloud.google.com/docs/authentication/set-up-adc-local-dev-environment).

```
const {
  VertexAI,
  FunctionDeclarationSchemaType,
} = require('@google-cloud/vertexai');

const functionDeclarations = [\\
  {\\
    function_declarations: [\\
      {\\
        name: 'get_current_weather',\\
        description: 'get weather in a given location',\\
        parameters: {\\
          type: FunctionDeclarationSchemaType.OBJECT,\\
          properties: {\\
            location: {type: FunctionDeclarationSchemaType.STRING},\\
            unit: {\\
              type: FunctionDeclarationSchemaType.STRING,\\
              enum: ['celsius', 'fahrenheit'],\\
            },\\
          },\\
          required: ['location'],\\
        },\\
      },\\
    ],\\
  },\\
];

const functionResponseParts = [\\
  {\\
    functionResponse: {\\
      name: 'get_current_weather',\\
      response: {name: 'get_current_weather', content: {weather: 'super nice'}},\\
    },\\
  },\\
];

/**
 * TODO(developer): Update these variables before running the sample.
 */
async function functionCallingStreamContent(
  projectId = 'PROJECT_ID',
  location = 'us-central1',
  model = 'gemini-1.5-flash-001'
) {
  // Initialize Vertex with your Cloud project and location
  const vertexAI = new VertexAI({project: projectId, location: location});

  // Instantiate the model
  const generativeModel = vertexAI.getGenerativeModel({
    model: model,
  });

  const request = {
    contents: [\\
      {role: 'user', parts: [{text: 'What is the weather in Boston?'}]},\\
      {\\
        role: 'ASSISTANT',\\
        parts: [\\
          {\\
            functionCall: {\\
              name: 'get_current_weather',\\
              args: {location: 'Boston'},\\
            },\\
          },\\
        ],\\
      },\\
      {role: 'USER', parts: functionResponseParts},\\
    ],
    tools: functionDeclarations,
  };
  const streamingResp = await generativeModel.generateContentStream(request);
  for await (const item of streamingResp.stream) {
    console.log(item.candidates[0].content.parts[0].text);
  }
}
```

### Go

This example demonstrates a text scenario with one function and one prompt.

### Go

Before trying this sample, follow the Go setup instructions in the
[Vertex AI quickstart using\\
client libraries](https://cloud.google.com/vertex-ai/docs/start/client-libraries).

For more information, see the
[Vertex AI Go API\\
reference documentation](https://cloud.google.com/go/docs/reference/cloud.google.com/go/aiplatform/latest/apiv1).

To authenticate to Vertex AI, set up Application Default Credentials.
For more information, see

[Set up authentication for a local development environment](https://cloud.google.com/docs/authentication/set-up-adc-local-dev-environment).

```
import (
	"context"
	"fmt"
	"io"

	genai "google.golang.org/genai"
)

// generateWithFuncCall shows how to submit a prompt and a function declaration to the model,
// allowing it to suggest a call to the function to fetch external data. Returning this data
// enables the model to generate a text response that incorporates the data.
func generateWithFuncCall(w io.Writer) error {
	ctx := context.Background()

	client, err := genai.NewClient(ctx, &genai.ClientConfig{
		HTTPOptions: genai.HTTPOptions{APIVersion: "v1"},
	})
	if err != nil {
		return fmt.Errorf("failed to create genai client: %w", err)
	}

	weatherFunc := &genai.FunctionDeclaration{
		Description: "Returns the current weather in a location.",
		Name:        "getCurrentWeather",
		Parameters: &genai.Schema{
			Type: "object",
			Properties: map[string]*genai.Schema{
				"location": {Type: "string"},
			},
			Required: []string{"location"},
		},
	}
	config := &genai.GenerateContentConfig{
		Tools: []*genai.Tool{
			{FunctionDeclarations: []*genai.FunctionDeclaration{weatherFunc}},
		},
		Temperature: genai.Ptr(0.0),
	}

	modelName := "gemini-2.0-flash-001"
	contents := []*genai.Content{
		{Parts: []*genai.Part{
			{Text: "What is the weather like in Boston?"},
		}},
	}

	resp, err := client.Models.GenerateContent(ctx, modelName, contents, config)
	if err != nil {
		return fmt.Errorf("failed to generate content: %w", err)
	}

	var funcCall *genai.FunctionCall
	for _, p := range resp.Candidates[0].Content.Parts {
		if p.FunctionCall != nil {
			funcCall = p.FunctionCall
			fmt.Fprint(w, "The model suggests to call the function ")
			fmt.Fprintf(w, "%q with args: %v\\n", funcCall.Name, funcCall.Args)
			// Example response:
			// The model suggests to call the function \"getCurrentWeather\" with args: map[location:Boston]
		}
	}
	if funcCall == nil {
		return fmt.Errorf("model did not suggest a function call")
	}

	// Use synthetic data to simulate a response from the external API.
	// In a real application, this would come from an actual weather API.
	funcResp := &genai.FunctionResponse{
		Name: "getCurrentWeather",
		Response: map[string]any{
			"location":         "Boston",
			"temperature":      "38",
			"temperature_unit": "F",
			"description":      "Cold and cloudy",
			"humidity":         "65",
			"wind":             `{\"speed\": \"10\", \"direction\": \"NW\"}`,
		},
	}

	// Return conversation turns and API response to complete the model's response.
	contents = []*genai.Content{
		{Parts: []*genai.Part{
			{Text: "What is the weather like in Boston?"},
		}},
		{Parts: []*genai.Part{
			{FunctionCall: funcCall},
		}},
		{Parts: []*genai.Part{
			{FunctionResponse: funcResp},
		}},
	}

	resp, err = client.Models.GenerateContent(ctx, modelName, contents, config)
	if err != nil {
		return fmt.Errorf("failed to generate content: %w", err)
	}

	respText, err := resp.Text()
	if err != nil {
		return fmt.Errorf("failed to convert model response to text: %w", err)
	}
	fmt.Fprintln(w, respText)

	// Example response:
	// The weather in Boston is cold and cloudy with a temperature of 38 degrees Fahrenheit. The humidity is ...

	return nil
}

```

### C\\#

This example demonstrates a text scenario with one function and one prompt.

### C\\#

Before trying this sample, follow the C# setup instructions in the
[Vertex AI quickstart using\\
client libraries](https://cloud.google.com/vertex-ai/docs/start/client-libraries).

For more information, see the
[Vertex AI C# API\\
reference documentation](https://cloud.google.com/dotnet/docs/reference/Google.Cloud.AIPlatform.V1/latest).

To authenticate to Vertex AI, set up Application Default Credentials.
For more information, see

[Set up authentication for a local development environment](https://cloud.google.com/docs/authentication/set-up-adc-local-dev-environment).

```

using Google.Cloud.AIPlatform.V1;
using System;
using System.Threading.Tasks;
using Type = Google.Cloud.AIPlatform.V1.Type;
using Value = Google.Protobuf.WellKnownTypes.Value;

public class FunctionCalling
{
    public async Task<string> GenerateFunctionCall(
        string projectId = \"your-project-id\",
        string location = \"us-central1\",
        string publisher = \"google\",
        string model = \"gemini-2.0-flash-001\")
    {
        var predictionServiceClient = new PredictionServiceClientBuilder
        {
            Endpoint = $\"{location}-aiplatform.googleapis.com\"
        }.Build();

        // Define the user's prompt in a Content object that we can reuse in
        // model calls
        var userPromptContent = new Content
        {
            Role = \"USER\",
            Parts =
            {
                new Part { Text = \"What is the weather like in Boston?\" }
            }
        };

        // Specify a function declaration and parameters for an API request
        var functionName = \"get_current_weather\";
        var getCurrentWeatherFunc = new FunctionDeclaration
        {
            Name = functionName,
            Description = \"Get the current weather in a given location\",
            Parameters = new OpenApiSchema
            {
                Type = Type.Object,
                Properties =
                {
                    [\"location\"] = new()
                    {
                        Type = Type.String,
                        Description = \"Get the current weather in a given location\"
                    },
                    [\"unit\"] = new()
                    {
                        Type = Type.String,
                        Description = \"The unit of measurement for the temperature\",
                        Enum = {\"celsius\", \"fahrenheit\"}
                    }
                },
                Required = { \"location\" }
            }
        };

        // Send the prompt and instruct the model to generate content using the tool that you just created
        var generateContentRequest = new GenerateContentRequest
        {
            Model = $\"projects/{projectId}/locations/{location}/publishers/{publisher}/models/{model}\",
            GenerationConfig = new GenerationConfig
            {
                Temperature = 0f
            },
            Contents =
            {
                userPromptContent
            },
            Tools =
            {
                new Tool
                {
                    FunctionDeclarations = { getCurrentWeatherFunc }
                }
            }
        };

        GenerateContentResponse response = await predictionServiceClient.GenerateContentAsync(generateContentRequest);

        var functionCall = response.Candidates[0].Content.Parts[0].FunctionCall;
        Console.WriteLine(functionCall);

        string apiResponse = \"\";

        // Check the function name that the model responded with, and make an API call to an external system
        if (functionCall.Name == functionName)
        {
            // Extract the arguments to use in your API call
            string locationCity = functionCall.Args.Fields[\"location\"].StringValue;

            // Here you can use your preferred method to make an API request to
            // fetch the current weather

            // In this example, we'll use synthetic data to simulate a response
            // payload from an external API
            apiResponse = @\"{\"\"location\"\": \"\"Boston, MA\"\",
                    \"\"temperature\"\": 38, \"\"description\"\": \"\"Partly Cloudy\"\"}\";
        }

        // Return the API response to Gemini so it can generate a model response or request another function call
        generateContentRequest = new GenerateContentRequest
        {
            Model = $\"projects/{projectId}/locations/{location}/publishers/{publisher}/models/{model}\",
            Contents =
            {
                userPromptContent, // User prompt
                response.Candidates[0].Content, // Function call response,
                new Content
                {
                    Parts =
                    {
                        new Part
                        {
                            FunctionResponse = new()
                            {
                                Name = functionName,
                                Response = new()
                                {
                                    Fields =
                                    {
                                        { \"content\", new Value { StringValue = apiResponse } }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            Tools =
            {
                new Tool
                {
                    FunctionDeclarations = { getCurrentWeatherFunc }
                }
            }
        };

        response = await predictionServiceClient.GenerateContentAsync(generateContentRequest);

        string responseText = response.Candidates[0].Content.Parts[0].Text;
        Console.WriteLine(responseText);

        return responseText;
    }
}

```

### REST

This example demonstrates a text scenario with three functions and
one prompt.

In this example, you call the generative AI model twice.

- In the [first call](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling#text-rest-first-request), you provide the model
with the prompt and the function declarations.
- In the [second call](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling#text-rest-second-request), you provide the
model with the API response.

#### First model request

The request must define a prompt in the `text` parameter. This example defines
the following prompt: \"Which theaters in Mountain View show the Barbie movie?\".

The request must also define a tool ( `tools`) with a set of function
declarations ( `functionDeclarations`). These function declarations must be
specified in a format that's compatible with the
[OpenAPI schema](https://spec.openapis.org/oas/v3.0.3#schema). This example
defines the following functions:

- `find_movies` finds movie titles playing in theaters.
- `find_theatres` finds theaters based on location.
- `get_showtimes` finds the start times for movies playing in a specific theater.

To learn more about the parameters of the model request, see
[Gemini API](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/gemini).

Replace my-project with the name of your Google Cloud project.

#### First model request

```
PROJECT_ID=my-project
MODEL_ID=gemini-2.0-flash-001
API=streamGenerateContent
curl -X POST -H \"Authorization: Bearer $(gcloud auth print-access-token)\" -H \"Content-Type: application/json\"  https://us-central1-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/us-central1/publishers/google/models/${MODEL_ID}:${API} -d '{
\"contents\": {
  \"role\": \"user\",
  \"parts\": {
    \"text\": \"Which theaters in Mountain View show the Barbie movie?\"
  }
},
\"tools\": [\\
  {\\
    \"function_declarations\": [\\
      {\\
        \"name\": \"find_movies\",\\
        \"description\": \"find movie titles currently playing in theaters based on any description, genre, title words, etc.\",\\
        \"parameters\": {\\
          \"type\": \"object\",\\
          \"properties\": {\\
            \"location\": {\\
              \"type\": \"string\",\\
              \"description\": \"The city and state, e.g. San Francisco, CA or a zip code e.g. 95616\"\\
            },\\
            \"description\": {\\
              \"type\": \"string\",\\
              \"description\": \"Any kind of description including category or genre, title words, attributes, etc.\"\
            }\\
          },\\
          \"required\": [\\
            \"description\"\\
          ]\\
        }\\
      },\\
      {\\
        \"name\": \"find_theaters\",\\
        \"description\": \"find theaters based on location and optionally movie title which are is currently playing in theaters\",\\
        \"parameters\": {\\
          \"type\": \"object\",\\
          \"properties\": {\\
            \"location\": {\\
              \"type\": \"string\",\\
              \"description\": \"The city and state, e.g. San Francisco, CA or a zip code e.g. 95616\"\\
            },\\
            \"movie\": {\\
              \"type\": \"string\",\\
              \"description\": \"Any movie title\"\\
            }\\
          },\\
          \"required\": [\\
            \"location\"\\
          ]\\
        }\\
      },\\
      {\\
        \"name\": \"get_showtimes\",\\
        \"description\": \"Find the start times for movies playing in a specific theater\",\\
        \"parameters\": {\\
          \"type\": \"object\",\\
          \"properties\": {\\
            \"location\": {\\
              \"type\": \"string\",\\
              \"description\": \"The city and state, e.g. San Francisco, CA or a zip code e.g. 95616\"\\
            },\\
            \"movie\": {\\
              \"type\": \"string\",\\
              \"description\": \"Any movie title\"\\
            },\\
            \"theater\": {\\
              \"type\": \"string\",\\
              \"description\": \"Name of the theater\"\\
            },\\
            \"date\": {\\
              \"type\": \"string\",\\
              \"description\": \"Date for requested showtime\"\\
            }\\
          },\\
          \"required\": [\\
            \"location\",\\
            \"movie\",\\
            \"theater\",\\
            \"date\"\\
          ]\\
        }\\
      }\\
    ]\\
  }\\
]
}'

```

For the prompt \"Which theaters in Mountain View show the Barbie movie?\", the model
might return the function `find_theatres` with parameters `Barbie` and
`Mountain View, CA`.

#### Response to first model request

```[{\\
\"candidates\": [\\
  {\\
    \"content\": {\\
      \"parts\": [\\
        {\\
          \"functionCall\": {\\
            \"name\": \"find_theaters\",\\
            \"args\": {\\
              \"movie\": \"Barbie\",\\
              \"location\": \"Mountain View, CA\"\\
            }\\
          }\\
        }\\
      ]\\
    },\\
    \"finishReason\": \"STOP\",\\
    \"safetyRatings\": [\\
      {\\
        \"category\": \"HARM_CATEGORY_HARASSMENT\",\\
        \"probability\": \"NEGLIGIBLE\"\\
      },\\
      {\\
        \"category\": \"HARM_CATEGORY_HATE_SPEECH\",\\
        \"probability\": \"NEGLIGIBLE\"\\
      },\\
      {\\
        \"category\": \"HARM_CATEGORY_SEXUALLY_EXPLICIT\",\\
        \"probability\": \"NEGLIGIBLE\"\\
      },\\
      {\\
        \"category\": \"HARM_CATEGORY_DANGEROUS_CONTENT\",\\
        \"probability\": \"NEGLIGIBLE\"\\
      }\\
    ]\\
  }\\
],\\
\"usageMetadata\": {\\
  \"promptTokenCount\": 9,\\
  \"totalTokenCount\": 9\\
}\\
}]

```

#### Second model request

This example uses synthetic data instead of calling the external API.
There are two results, each with two parameters ( `name` and `address`):

1. `name`: `AMC Mountain View 16`,
`address`: `2000 W El Camino Real, Mountain View, CA 94040`
2. `name`: `Regal Edwards 14`,
`address`: `245 Castro St, Mountain View, CA 94040`

Replace my-project with the name of your Google Cloud project.

#### Second model request

```
PROJECT_ID=my-project
MODEL_ID=gemini-2.0-flash-001
API=streamGenerateContent
curl -X POST -H \"Authorization: Bearer $(gcloud auth print-access-token)\" -H \"Content-Type: application/json\"  https://us-central1-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/us-central1/publishers/google/models/${MODEL_ID}:${API} -d '{
\"contents\": [{\\
  \"role\": \"user\",\\
  \"parts\": [{\\
    \"text\": \"Which theaters in Mountain View show the Barbie movie?\"\\
  }]\\
}, {\\
  \"role\": \"model\",\\
  \"parts\": [{\\
    \"functionCall\": {\\
      \"name\": \"find_theaters\",\\
      \"args\": {\\
        \"location\": \"Mountain View, CA\",\\
        \"movie\": \"Barbie\"\\
      }\\
    }\\
  }]\\
}, {\\
  \"parts\": [{\\
    \"functionResponse\": {\\
      \"name\": \"find_theaters\",\\
      \"response\": {\\
        \"name\": \"find_theaters\",\\
        \"content\": {\\
          \"movie\": \"Barbie\",\\
          \"theaters\": [{\\
            \"name\": \"AMC Mountain View 16\",\\
            \"address\": \"2000 W El Camino Real, Mountain View, CA 94040\"\\
          }, {\\
            \"name\": \"Regal Edwards 14\",\\
            \"address\": \"245 Castro St, Mountain View, CA 94040\"\\
          }]\\
        }\\
      }\\
    }\\
  }]\\
}],
\"tools\": [{\\
  \"functionDeclarations\": [{\\
    \"name\": \"find_movies\",\\
    \"description\": \"find movie titles currently playing in theaters based on any description, genre, title words, etc.\",\\
    \"parameters\": {\\
      \"type\": \"OBJECT\",\\
      \"properties\": {\\
        \"location\": {\\
          \"type\": \"STRING\",\\
          \"description\": \"The city and state, e.g. San Francisco, CA or a zip code e.g. 95616\"\\
        },\\
        \"description\": {\\
          \"type\": \"STRING\",\\
          \"description\": \"Any kind of description including category or genre, title words, attributes, etc.\"\
        }\\
      },\\
      \"required\": [\"description\"]\\
    }\\
  }, {\\
    \"name\": \"find_theaters\",\\
    \"description\": \"find theaters based on location and optionally movie title which are is currently playing in theaters\",\\
    \"parameters\": {\\
      \"type\": \"OBJECT\",\\
      \"properties\": {\\
        \"location\": {\\
          \"type\": \"STRING\",\\
          \"description\": \"The city and state, e.g. San Francisco, CA or a zip code e.g. 95616\"\\
        },\\
        \"movie\": {\\
          \"type\": \"STRING\",\\
          \"description\": \"Any movie title\"\\
        }\\
      },\\
      \"required\": [\"location\"]\\
    }\\
  }, {\\
    \"name\": \"get_showtimes\",\\
    \"description\": \"Find the start times for movies playing in a specific theater\",\\
    \"parameters\": {\\
      \"type\": \"OBJECT\",\\
      \"properties\": {\\
        \"location\": {\\
          \"type\": \"STRING\",\\
          \"description\": \"The city and state, e.g. San Francisco, CA or a zip code e.g. 95616\"\\
        },\\
        \"movie\": {\\
          \"type\": \"STRING\",\\
          \"description\": \"Any movie title\"\\
        },\\
        \"theater\": {\\
          \"type\": \"STRING\",\\
          \"description\": \"Name of the theater\"\\
        },\\
        \"date\": {\\
          \"type\": \"STRING\",\\
          \"description\": \"Date for requested showtime\"\\
        }\\
      },\\
      \"required\": [\"location\", \"movie\", \"theater\", \"date\"]\\
    }\\
  }]\\
}]
}'

```

The model's response might be similar to the following:

#### Response to second model request

```
{
\"candidates\": [\\
  {\\
    \"content\": {\\
      \"parts\": [\\
        {\\
          \"text\": \" OK. Barbie is showing in two theaters in Mountain View, CA: AMC Mountain View 16 and Regal Edwards 14.\"\\
        }\\
      ]\\
    }\\
  }\\
],
\"usageMetadata\": {
  \"promptTokenCount\": 9,
  \"candidatesTokenCount\": 27,
  \"totalTokenCount\": 36
}
}

```

### Chat examples

You can use function calling to support a chat session. Chat sessions are useful
in freeform, conversational scenarios, where a user is likely to ask follow-up
questions.

If you use function calling in the context of a chat session, the session stores
the context for you and includes it in every model request.
Vertex AI stores the history of the interaction on the client side.

### Java

Before trying this sample, follow the Java setup instructions in the
[Vertex AI quickstart using\\
client libraries](https://cloud.google.com/vertex-ai/docs/start/client-libraries).

For more information, see the
[Vertex AI Java API\\
reference documentation](https://cloud.google.com/java/docs/reference/google-cloud-aiplatform/latest/com.google.cloud.aiplatform.v1).

To authenticate to Vertex AI, set up Application Default Credentials.
For more information, see

[Set up authentication for a local development environment](https://cloud.google.com/docs/authentication/set-up-adc-local-dev-environment).

```
import com.google.cloud.vertexai.VertexAI;
import com.google.cloud.vertexai.api.Content;
import com.google.cloud.vertexai.api.FunctionDeclaration;
import com.google.cloud.vertexai.api.GenerateContentResponse;
import com.google.cloud.vertexai.api.Schema;
import com.google.cloud.vertexai.api.Tool;
import com.google.cloud.vertexai.api.Type;
import com.google.cloud.vertexai.generativeai.ChatSession;
import com.google.cloud.vertexai.generativeai.ContentMaker;
import com.google.cloud.vertexai.generativeai.GenerativeModel;
import com.google.cloud.vertexai.generativeai.PartMaker;
import com.google.cloud.vertexai.generativeai.ResponseHandler;
import java.io.IOException;
import java.util.Arrays;
import java.util.Collections;

public class FunctionCalling {
  public static void main(String[] args) throws IOException {
    // TODO(developer): Replace these variables before running the sample.
    String projectId = \"your-google-cloud-project-id\";
    String location = \"us-central1\";
    String modelName = \"gemini-1.5-flash-001\";

    String promptText = \"What's the weather like in Paris?\";

    whatsTheWeatherLike(projectId, location, modelName, promptText);
  }

  // A request involving the interaction with an external tool
  public static String whatsTheWeatherLike(String projectId, String location,
                                           String modelName, String promptText)
      throws IOException {
    // Initialize client that will be used to send requests.
    // This client only needs to be created once, and can be reused for multiple requests.
    try (VertexAI vertexAI = new VertexAI(projectId, location)) {

      FunctionDeclaration functionDeclaration = FunctionDeclaration.newBuilder()
          .setName(\"getCurrentWeather\")
          .setDescription(\"Get the current weather in a given location\")
          .setParameters(
              Schema.newBuilder()
                  .setType(Type.OBJECT)
                  .putProperties(\"location\", Schema.newBuilder()
                      .setType(Type.STRING)
                      .setDescription(\"location\")
                      .build()
                  )
                  .addRequired(\"location\")
                  .build()
          )
          .build();

      System.out.println(\"Function declaration:\");
      System.out.println(functionDeclaration);

      // Add the function to a \"tool\"
      Tool tool = Tool.newBuilder()
          .addFunctionDeclarations(functionDeclaration)
          .build();

      // Start a chat session from a model, with the use of the declared function.
      GenerativeModel model = new GenerativeModel(modelName, vertexAI)
          .withTools(Arrays.asList(tool));
      ChatSession chat = model.startChat();

      System.out.println(String.format(\"Ask the question: %s\", promptText));
      GenerateContentResponse response = chat.sendMessage(promptText);

      // The model will most likely return a function call to the declared
      // function `getCurrentWeather` with \"Paris\" as the value for the
      // argument `location`.
      System.out.println(\"\\nPrint response: \");
      System.out.println(ResponseHandler.getContent(response));

      // Provide an answer to the model so that it knows what the result
      // of a \"function call\" is.
      Content content =
          ContentMaker.fromMultiModalData(
              PartMaker.fromFunctionResponse(
                  \"getCurrentWeather\",
                  Collections.singletonMap(\"currentWeather\", \"sunny\")));
      System.out.println(\"Provide the function response: \");
      System.out.println(content);
      response = chat.sendMessage(content);

      // See what the model replies now
      System.out.println(\"Print response: \");
      String finalAnswer = ResponseHandler.getText(response);
      System.out.println(finalAnswer);

      return finalAnswer;
    }
  }
}
```

### Go

Before trying this sample, follow the Go setup instructions in the
[Vertex AI quickstart using\\
client libraries](https://cloud.google.com/vertex-ai/docs/start/client-libraries).

For more information, see the
[Vertex AI Go API\\
reference documentation](https://cloud.google.com/go/docs/reference/cloud.google.com/go/aiplatform/latest/apiv1).

To authenticate to Vertex AI, set up Application Default Credentials.
For more information, see

[Set up authentication for a local development environment](https://cloud.google.com/docs/authentication/set-up-adc-local-dev-environment).

```
import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"

	"cloud.google.com/go/vertexai/genai"
)

// functionCallsChat opens a chat session and sends 4 messages to the model:
// - convert a first text question into a structured function call request
// - convert the first structured function call response into natural language
// - convert a second text question into a structured function call request
// - convert the second structured function call response into natural language
func functionCallsChat(w io.Writer, projectID, location, modelName string) error {
	// location := \"us-central1\"
	// modelName := \"gemini-1.5-flash-001\"
	ctx := context.Background()
	client, err := genai.NewClient(ctx, projectID, location)
	if err != nil {
		return fmt.Errorf("unable to create client: %w", err)
	}
	defer client.Close()

	model := client.GenerativeModel(modelName)

	// Build an OpenAPI schema, in memory
	paramsProduct := &genai.Schema{
		Type: genai.TypeObject,
		Properties: map[string]*genai.Schema{
			"productName": {
				Type:        genai.TypeString,
				Description: "Product name",
			},
		},
	}
	fundeclProductInfo := &genai.FunctionDeclaration{
		Name:        "getProductSku",
		Description: "Get the SKU for a product",
		Parameters:  paramsProduct,
	}
	paramsStore := &genai.Schema{
		Type: genai.TypeObject,
		Properties: map[string]*genai.Schema{
			"location": {
				Type:        genai.TypeString,
				Description: "Location",
			},
		},
	}
	fundeclStoreLocation := &genai.FunctionDeclaration{
		Name:        "getStoreLocation",
		Description: "Get the location of the closest store",
		Parameters:  paramsStore,
	}
	model.Tools = []*genai.Tool{
		{FunctionDeclarations: []*genai.FunctionDeclaration{
			fundeclProductInfo,
			fundeclStoreLocation,
		}},
	}
	model.SetTemperature(0.0)

	chat := model.StartChat()

	// Send a prompt for the first conversation turn that should invoke the getProductSku function
	prompt := \"Do you have the Pixel 8 Pro in stock?\"
	fmt.Fprintf(w, \"Question: %s\\n\", prompt)
	resp, err := chat.SendMessage(ctx, genai.Text(prompt))
	if err != nil {
		return err
	}
	if len(resp.Candidates) == 0 ||
		len(resp.Candidates[0].Content.Parts) == 0 {
		return errors.New("empty response from model")
	}

	// The model has returned a function call to the declared function `getProductSku`
	// with a value for the argument `productName`.
	jsondata, err := json.MarshalIndent(resp.Candidates[0].Content.Parts[0], \"\\t\", \"  \")
	if err != nil {
		return fmt.Errorf("json.MarshalIndent: %w", err)
	}
	fmt.Fprintf(w, \"function call generated by the model:\\n\\t%s\\n\", string(jsondata))

	// Create a function call response, to simulate the result of a call to a
	// real service
	funresp := &genai.FunctionResponse{
		Name: \"getProductSku\",
		Response: map[string]any{
			"sku":      "GA04834-US",
			"in_stock": "yes",
		},
	}
	jsondata, err = json.MarshalIndent(funresp, \"\\t\", \"  \")
	if err != nil {
		return fmt.Errorf("json.MarshalIndent: %w", err)
	}
	fmt.Fprintf(w, \"function call response sent to the model:\\n\\t%s\\n\\n\", string(jsondata))

	// And provide the function call response to the model
	resp, err = chat.SendMessage(ctx, funresp)
	if err != nil {
		return err
	}
	if len(resp.Candidates) == 0 ||
		len(resp.Candidates[0].Content.Parts) == 0 {
		return errors.New("empty response from model")
	}

	// The model has taken the function call response as input, and has
	// reformulated the response to the user.
	jsondata, err = json.MarshalIndent(resp.Candidates[0].Content.Parts[0], \"\\t\", \"  \")
	if err != nil {
		return fmt.Errorf("json.MarshalIndent: %w", err)
	}
	fmt.Fprintf(w, \"Answer generated by the model:\\n\\t%s\\n\\n\", string(jsondata))

	// Send a prompt for the second conversation turn that should invoke the getStoreLocation function
	prompt2 := \"Is there a store in Mountain View, CA that I can visit to try it out?\"
	fmt.Fprintf(w, \"Question: %s\\n\", prompt)

	resp, err = chat.SendMessage(ctx, genai.Text(prompt2))
	if err != nil {
		return err
	}
	if len(resp.Candidates) == 0 ||
		len(resp.Candidates[0].Content.Parts) == 0 {
		return errors.New("empty response from model")
	}

	// The model has returned a function call to the declared function `getStoreLocation`
	// with a value for the argument `store`.
	jsondata, err = json.MarshalIndent(resp.Candidates[0].Content.Parts[0], \"\\t\", \"  \")
	if err != nil {
		return fmt.Errorf("json.MarshalIndent: %w", err)
	}
	fmt.Fprintf(w, \"function call generated by the model:\\n\\t%s\\n\", string(jsondata))

	// Create a function call response, to simulate the result of a call to a
	// real service
	funresp = &genai.FunctionResponse{
		Name: \"getStoreLocation\",
		Response: map[string]any{
			"store": \"2000 N Shoreline Blvd, Mountain View, CA 94043, US\",
		},
	}
	jsondata, err = json.MarshalIndent(funresp, \"\\t\", \"  \")
	if err != nil {
		return fmt.Errorf("json.MarshalIndent: %w", err)
	}
	fmt.Fprintf(w, \"function call response sent to the model:\\n\\t%s\\n\\n\", string(jsondata))

	// And provide the function call response to the model
	resp, err = chat.SendMessage(ctx, funresp)
	if err != nil {
		return err
	}
	if len(resp.Candidates) == 0 ||
		len(resp.Candidates[0].Content.Parts) == 0 {
		return errors.New("empty response from model")
	}

	// The model has taken the function call response as input, and has
	// reformulated the response to the user.
	jsondata, err = json.MarshalIndent(resp.Candidates[0].Content.Parts[0], \"\\t\", \"  \")
	if err != nil {
		return fmt.Errorf("json.MarshalIndent: %w", err)
	}
	fmt.Fprintf(w, \"Answer generated by the model:\\n\\t%s\\n\\n\", string(jsondata))
	return nil
}

```

### Node.js

Before trying this sample, follow the Node.js setup instructions in the
[Vertex AI quickstart using\\
client libraries](https://cloud.google.com/vertex-ai/docs/start/client-libraries).

For more information, see the
[Vertex AI Node.js API\\
reference documentation](https://cloud.google.com/nodejs/docs/reference/aiplatform/latest).

To authenticate to Vertex AI, set up Application Default Credentials.
For more information, see

[Set up authentication for a local development environment](https://cloud.google.com/docs/authentication/set-up-adc-local-dev-environment).

```
const {
  VertexAI,
  FunctionDeclarationSchemaType,
} = require('@google-cloud/vertexai');

const functionDeclarations = [\\
  {\\
    function_declarations: [\\
      {\\
        name: 'get_current_weather',\\
        description: 'get weather in a given location',\\
        parameters: {\\
          type: FunctionDeclarationSchemaType.OBJECT,\\
          properties: {\\
            location: {type: FunctionDeclarationSchemaType.STRING},\\
            unit: {\\
              type: FunctionDeclarationSchemaType.STRING,\\
              enum: ['celsius', 'fahrenheit'],\\
            },\\
          },\\
          required: ['location'],\\
        },\\
      },\\
    ],\\
  },\\
];

const functionResponseParts = [\\
  {\\
    functionResponse: {\\
      name: 'get_current_weather',\\
      response: {name: 'get_current_weather', content: {weather: 'super nice'}},\\
    },\\
  },\\
];

/**
 * TODO(developer): Update these variables before running the sample.
 */
async function functionCallingStreamChat(
  projectId = 'PROJECT_ID',
  location = 'us-central1',
  model = 'gemini-1.5-flash-001'
) {
  // Initialize Vertex with your Cloud project and location
  const vertexAI = new VertexAI({project: projectId, location: location});

  // Instantiate the model
  const generativeModel = vertexAI.getGenerativeModel({
    model: model,
  });

  // Create a chat session and pass your function declarations
  const chat = generativeModel.startChat({
    tools: functionDeclarations,
  });

  const chatInput1 = 'What is the weather in Boston?';

  // This should include a functionCall response from the model
  const result1 = await chat.sendMessageStream(chatInput1);
  for await (const item of result1.stream) {
    console.log(item.candidates[0]);
  }
  await result1.response;

  // Send a follow up message with a FunctionResponse
  const result2 = await chat.sendMessageStream(functionResponseParts);
  for await (const item of result2.stream) {
    console.log(item.candidates[0]);
  }

  // This should include a text response from the model using the response content
  // provided above
  const response2 = await result2.response;
  console.log(response2.candidates[0].content.parts[0].text);
}
```

## Parallel function calling example

For prompts such as \"Get weather details in New Delhi and San Francisco?\",
the model may propose several parallel function calls. For a list of models that
support parallel function calling, see [Supported models](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling#supported_models).

### REST

This example demonstrates a scenario with one `get_current_weather` function.
The user prompt is \"Get weather details in New Delhi and San Francisco?\". The
model proposes two parallel `get_current_weather` function calls: one with the
parameter `New Delhi` and the other with the parameter `San Francisco`.

To learn more about the parameters of the model request, see
[Gemini API](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/gemini).

```
{
\"candidates\": [\\
  {\\
    \"content\": {\\
      \"role\": \"model\",\\
      \"parts\": [\\
        {\\
          \"functionCall\": {\\
            \"name\": \"get_current_weather\",\\
            \"args\": {\\
              \"location\": \"New Delhi\"\\
            }\\
          }\\
        },\\
        {\\
          \"functionCall\": {\\
            \"name\": \"get_current_weather\",\\
            \"args\": {\\
              \"location\": \"San Francisco\"\\
            }\\
          }\\
        }\\
      ]\\
    },\\
    ...\\
  }\\
],
...
}

```

The following command demonstrates how you can provide the function output to
the model. Replace my-project with the name of your Google Cloud project.

#### Model request

```
PROJECT_ID=my-project
MODEL_ID=gemini-2.0-flash
VERSION=\"v1\"
LOCATION=\"us-central1\"
ENDPOINT=${LOCATION}-aiplatform.googleapis.com
API=\"generateContent\"
curl -X POST -H \"Authorization: Bearer $(gcloud auth print-access-token)\" -H \"Content-Type: application/json\"  https://${ENDPOINT}/${VERSION}/projects/${PROJECT_ID}/locations/${LOCATION}/publishers/google/models/${MODEL_ID}:${API} -d '{
\"contents\": [\\
    {\\
        \"role\": \"user\",\\
        \"parts\": {\\
            \"text\": \"What is difference in temperature in New Delhi and San Francisco?\"\\
        }\\
    },\\
    {\\
        \"role\": \"model\",\\
        \"parts\": [\\
            {\\
                \"functionCall\": {\\
                    \"name\": \"get_current_weather\",\\
                    \"args\": {\\
                        \"location\": \"New Delhi\"\\
                    }\\
                }\\
            },\\
            {\\
                \"functionCall\": {\\
                    \"name\": \"get_current_weather\",\\
                    \"args\": {\\
                        \"location\": \"San Francisco\"\\
                    }\\
                }\\
            }\\
        ]\\
    },\\
    {\\
        \"role\": \"user\",\\
        \"parts\": [\\
            {\\
                \"functionResponse\": {\\
                    \"name\": \"get_current_weather\",\\
                    \"response\": {\\
                        \"temperature\": 30.5,\\
                        \"unit\": \"C\"\\
                    }\\
                }\\
            },\\
            {\\
                \"functionResponse\": {\\
                    \"name\": \"get_current_weather\",\\
                    \"response\": {\\
                        \"temperature\": 20,\\
                        \"unit\": \"C\"\\
                    }\\
                }\\
            }\\
        ]\\
    }\\
],
\"tools\": [\\
    {\\
        \"function_declarations\": [\\
            {\\
                \"name\": \"get_current_weather\",\\
                \"description\": \"Get the current weather in a specific location\",\\
                \"parameters\": {\\
                    \"type\": \"object\",\\
                    \"properties\": {\\
                        \"location\": {\\
                            \"type\": \"string\",\\
                            \"description\": \"The city and state, e.g. San Francisco, CA or a zip code e.g. 95616\"\\
                        }\\
                    },\\
                    \"required\": [\\
                        \"location\"\\
                    ]\\
                }\\
            }\\
        ]\\
    }\\
]
}'

```

The natural language response created by the model is similar to the following:

#### Model response

```
[\\
{\\
    \"candidates\": [\\
        {\\
            \"content\": {\\
                \"parts\": [\\
                    {\\
                        \"text\": \"The temperature in New Delhi is 30.5C and the temperature in San Francisco is 20C. The difference is 10.5C. \\n\"\\
                    }\\
                ]\\
            },\\
            \"finishReason\": \"STOP\",\\
            ...\\
        }\\
    ]\\
    ...\\
}\\
]

```

### Go

```
import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"

	"cloud.google.com/go/vertexai/genai"
)

// parallelFunctionCalling shows how to execute multiple function calls in parallel
// and return their results to the model for generating a complete response.
func parallelFunctionCalling(w io.Writer, projectID, location, modelName string) error {
	// location = \"us-central1\"
	// modelName = \"gemini-1.5-flash-002\"
	ctx := context.Background()
	client, err := genai.NewClient(ctx, projectID, location)
	if err != nil {
		return fmt.Errorf("failed to create GenAI client: %w", err)
	}
	defer client.Close()

	model := client.GenerativeModel(modelName)
	// Set temperature to 0.0 for maximum determinism in function calling.
	model.SetTemperature(0.0)

	funcName := \"getCurrentWeather\"
	funcDecl := &genai.FunctionDeclaration{
		Name:        funcName,
		Description: \"Get the current weather in a given location\",
		Parameters: &genai.Schema{
			Type: genai.TypeObject,
			Properties: map[string]*genai.Schema{
				"location": {
					Type: genai.TypeString,
					Description: \"The location for which to get the weather. \" +
						"It can be a city name, a city name and state, or a zip code. \" +
						"Examples: 'San Francisco', 'San Francisco, CA', '95616', etc.\",
				},
			},
			Required: []string{"location"},
		},
	}
	// Add the weather function to our model toolbox.
	model.Tools = []*genai.Tool{
		{
			FunctionDeclarations: []*genai.FunctionDeclaration{funcDecl},
		},
	}

	prompt := genai.Text("Get weather details in New Delhi and San Francisco?")
	resp, err := model.GenerateContent(ctx, prompt)

	if err != nil {
		return fmt.Errorf("failed to generate content: %w", err)
	}
	if len(resp.Candidates) == 0 {
		return errors.New("got empty response from model")
	} else if len(resp.Candidates[0].FunctionCalls()) == 0 {
		return errors.New("got no function call suggestions from model")
	}

	// In a production environment, consider adding validations for function names and arguments.
	for _, fnCall := range resp.Candidates[0].FunctionCalls() {
		fmt.Fprintf(w, \"The model suggests to call the function %q with args: %v\\n\", fnCall.Name, fnCall.Args)
		// Example response:
		// The model suggests to call the function \"getCurrentWeather\" with args: map[location:New Delhi]
		// The model suggests to call the function \"getCurrentWeather\" with args: map[location:San Francisco]
	}

	// Use synthetic data to simulate responses from the external API.
	// In a real application, this would come from an actual weather API.
	mockAPIResp1, err := json.Marshal(map[string]string{
		"location":         "New Delhi",
		"temperature":      "42",
		"temperature_unit": "C",
		"description":      "Hot and humid",
		"humidity":         "65",
	})
	if err != nil {
		return fmt.Errorf("failed to marshal function response to JSON: %w", err)
	}

	mockAPIResp2, err := json.Marshal(map[string]string{
		"location":         "San Francisco",
		"temperature":      "36",
		"temperature_unit": "F",
		"description":      "Cold and cloudy",
		"humidity":         "N/A",
	})
	if err != nil {
		return fmt.Errorf("failed to marshal function response to JSON: %w", err)
	}

	// Note, that the function calls don't have to be chained. We can obtain both responses in parallel
	// and return them to Gemini at once.
	funcResp1 := &genai.FunctionResponse{
		Name: funcName,
		Response: map[string]any{
			"content": mockAPIResp1,
		},
	}
	funcResp2 := &genai.FunctionResponse{
		Name: funcName,
		Response: map[string]any{
			"content": mockAPIResp2,
		},
	}

	// Return both API responses to the model allowing it to complete its response.
	resp, err = model.GenerateContent(ctx, prompt, funcResp1, funcResp2)
	if err != nil {
		return fmt.Errorf("failed to generate content: %w", err)
	}
	if len(resp.Candidates) == 0 || len(resp.Candidates[0].Content.Parts) == 0 {
		return errors.New("got empty response from model")
	}

	fmt.Fprintln(w, resp.Candidates[0].Content.Parts[0])
	// Example response:
	// The weather in New Delhi is hot and humid with a humidity of 65 and a temperature of 42°C. The weather in San Francisco ...

	return nil
}

```

## Best practices for function calling

### Function name

Function name should start with a letter or an underscore and contains only characters a-z, A-Z, 0-9, underscores, dots or dashes with a maximum length of 64.

### Function description

Write function descriptions clearly and verbosely. For example, for a
`book_flight_ticket` function:

- The following is an example of a good function description:
`book flight tickets after confirming users' specific requirements, such as time, departure, destination, party size and preferred airline`
- The following is an example of a bad function description:
`book flight ticket`

### Function parameters

Function parameter and nested attribute names should start with a letter or an underscore and contains only characters a-z, A-Z, 0-9, or underscores with a maximum length of 64. Don't use period ( `.`), dash ( `-`), or space characters in the function parameter names and nested attributes.
Instead, use underscore ( `_`) characters or any other characters.

#### Descriptions

Write clear and verbose parameter descriptions, including details such as your
preferred format or values. For example, for
a `book_flight_ticket` function:

- The following is a good example of a `departure` parameter description:
`Use the 3 char airport code to represent the airport. For example, SJC or SFO. Don't use the city name.`
- The following is a bad example of a `departure` parameter description:
`the departure airport`

#### Types

If possible, use strongly typed parameters to reduce model hallucinations. For
example, if the parameter values are from a finite set, add an `enum` field
instead of putting the set of values into the description. If the parameter
value is always an integer, set the type to `integer` rather than `number`.

#### System instructions

When using functions with date, time, or location parameters, include the
current date, time, or relevant location information (for example, city and
country) in the system instruction. This ensures the model has the necessary
context to process the request accurately, even if the user's prompt lacks
details.

### User prompt

For best results, prepend the user prompt with the following details:

- Additional context for the model-for example, `You are a flight API assistant to help with searching flights based on user preferences.`
- Details or instructions on how and when to use the functions-for example, `Don't make assumptions on the departure or destination airports. Always use a future date for the departure or destination time.`
- Instructions to ask clarifying questions if user queries are ambiguous-for example, `Ask clarifying questions if not enough information is available.`

### Generation configuration

For the temperature parameter, use `0` or another low value. This instructs
the model to generate more confident results and reduces hallucinations.

### API invocation

If the model proposes the invocation of a function that would send an order,
update a database, or otherwise have significant consequences, validate the
function call with the user before executing it.

## Pricing

The pricing for function calling is based on the number of characters within the
text inputs and outputs. To learn more, see
[Vertex AI pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing).

Here, text input (prompt)
refers to the user prompt for the current conversation turn, the function
declarations for the current conversation turn, and the history of the
conversation. The history of the conversation includes the queries, the function
calls, and the function responses of previous conversation turns.
Vertex AI truncates the history of the conversation at 32,000 characters.

Text output (response) refers to the function calls and the text responses
for the current conversation turn.

## What's next

- See the [API reference for function calling](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/function-calling).

- Learn about [Vertex AI extensions](https://cloud.google.com/vertex-ai/generative-ai/docs/extensions/overview).

- Learn about [LangChain on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/reasoning-engine/overview).

 Send feedback

Except as otherwise noted, the content of this page is licensed under the [Creative Commons Attribution 4.0 License](https://creativecommons.org/licenses/by/4.0/), and code samples are licensed under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0). For details, see the [Google Developers Site Policies](https://developers.google.com/site-policies). Java is a registered trademark of Oracle and/or its affiliates.

Last updated 2025-04-12 UTC.
```

**3. URL: https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/content-generation-parameters**

```markdown
[Skip to main content](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/content-generation-parameters#main-content)

[![Google Cloud](https://www.gstatic.com/devrel-devsite/prod/vd31e3ed8994e05c7f2cd0cf68a402ca7902bb92b6ec0977d7ef2a1c699fae3f9/cloud/images/cloud-logo.svg)](https://cloud.google.com/)

`/`

- English
- Deutsch
- Español – América Latina
- Français
- Indonesia
- Italiano
- Português – Brasil
- 中文 – 简体
- 日本語
- 한국어

[Console](https://console.cloud.google.com/)Sign in

- [Generative AI on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/overview)

[Contact Us](https://cloud.google.com/contact) [Start free](https://console.cloud.google.com/freetrial)

- [Home](https://cloud.google.com/)
- [Generative AI on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/overview)
- [Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/overview)

 Send feedback

# Content generation parameters       Stay organized with collections     Save and categorize content based on your preferences.

This page shows the optional sampling parameters you can set in a request to a
model. The parameters available for each model may differ. For more information,
see the [reference documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference#generationconfig).

## Token sampling parameters

### Top-P

Top-P changes how the model selects tokens for output. Tokens are selected
from the most (see top-K) to least probable until the sum of their probabilities
equals the top-P value. For example, if tokens A, B, and C have a probability of
0.3, 0.2, and 0.1 and the top-P value is `0.5`, then the model will
select either A or B as the next token by using temperature and excludes C as a
candidate.

Specify a lower value for less random responses and a higher value for more
random responses.

For more information, see [`topP`](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference#topP).

### Top-K

Top-K changes how the model selects tokens for output. A top-K of
`1` means the next selected token is the most probable among all
tokens in the model's vocabulary (also called greedy decoding), while a top-K of
`3` means that the next token is selected from among the three most
probable tokens by using temperature.

For each token selection step, the top-K tokens with the highest
probabilities are sampled. Then tokens are further filtered based on top-P with
the final token selected using temperature sampling.

Specify a lower value for less random responses and a higher value for more
random responses.

For more information, see [`topK`](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference#topK).

### Temperature

The temperature is used for sampling during response generation, which occurs when `topP`
and `topK` are applied. Temperature controls the degree of randomness in token selection.
Lower temperatures are good for prompts that require a less open-ended or creative response, while
higher temperatures can lead to more diverse or creative results. A temperature of `0`
means that the highest probability tokens are always selected. In this case, responses for a given
prompt are mostly deterministic, but a small amount of variation is still possible.

If the model returns a response that's too generic, too short, or the model gives a fallback
response, try increasing the temperature.

Lower temperatures lead to predictable (but not completely [deterministic](https://medium.com/google-cloud/is-a-zero-temperature-deterministic-c4a7faef4d20))
results. For more information, see [`temperature`](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference#temperature).

## Stopping parameters

### Maximum output tokens

Set [`maxOutputTokens`](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference#maxOutputTokens) to limit the number of tokens
generated in the response. A token is approximately four characters, so 100
tokens correspond to roughly 60-80 words. Set a low value to limit the length
of the response.

### Stop sequences

Define strings in [`stopSequences`](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference#stopSequences) to tell the model to stop
generating text if one of the strings is encountered in the response. If a
string appears multiple times in the response, then the response is truncated
where the string is first encountered. The strings are case-sensitive.

## Token penalization parameters

### Frequency penalty

Positive values penalize tokens that repeatedly appear in the generated text, decreasing the
probability of repeating content. The minimum value is `-2.0`. The maximum value is up
to, but not including, `2.0`.
For more information, see [`frequencyPenalty`](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference#frequencyPenalty).

### Presence penalty

Positive values penalize tokens that already appear in the generated text, increasing the
probability of generating more diverse content. The minimum value is `-2.0`. The maximum
value is up to, but not including, `2.0`.
For more information, see [`presencePenalty`](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference#presencePenalty).

## Advanced parameters

Use these parameters to return more information about the tokens in the response
or to control the variability of the response.

### Log probabilities of output tokens

Returns the log probabilities of the top candidate tokens at each generation step. The model's
chosen token might not be the same as the top candidate token at each step. Specify the number of
candidates to return by using an integer value in the range of `1`- `5`.
For more information, see [`logprobs`](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference#logprobs). You also need to
set the [`responseLogprobs`](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference#responseLogprobs) parameter to `true` to use this
feature.

The [`responseLogprobs`](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference#responseLogprobs) parameter returns the log
probabilities of the tokens that were chosen by the model at each step.

### Seed

When seed is fixed to a specific value, the model makes a best effort to provide
the same response for repeated requests. Deterministic output isn't guaranteed.
Also, changing the model or parameter settings, such as the temperature, can
cause variations in the response even when you use the same seed value. By
default, a random seed value is used.
For more information, see [`seed`](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference#seed).

 Send feedback

Except as otherwise noted, the content of this page is licensed under the [Creative Commons Attribution 4.0 License](https://creativecommons.org/licenses/by/4.0/), and code samples are licensed under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0). For details, see the [Google Developers Site Policies](https://developers.google.com/site-policies). Java is a registered trademark of Oracle and/or its affiliates.

Last updated 2025-04-12 UTC.
```

**4. URL: https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/code-execution-api**

```markdown
[Skip to main content](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/code-execution-api#main-content)

[![Google Cloud](https://www.gstatic.com/devrel-devsite/prod/vd31e3ed8994e05c7f2cd0cf68a402ca7902bb92b6ec0977d7ef2a1c699fae3f9/cloud/images/cloud-logo.svg)](https://cloud.google.com/)

`/`

- English
- Deutsch
- Español – América Latina
- Français
- Indonesia
- Italiano
- Português – Brasil
- 中文 – 简体
- 日本語
- 한국어

[Console](https://console.cloud.google.com/)Sign in

- [Generative AI on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/overview)

[Contact Us](https://cloud.google.com/contact) [Start free](https://console.cloud.google.com/freetrial)

- [Home](https://cloud.google.com/)
- [Generative AI on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/overview)
- [Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/overview)

 Send feedback

# Execute code with the Gemini Enterprise API       Stay organized with collections     Save and categorize content based on your preferences.

The Gemini API code execution feature enables the model to generate and run
Python code and learn iteratively from the results until it arrives at a final
output. You can use this code execution capability to build applications that
benefit from code-based reasoning and that produce text output. For example,
you could use code execution in an application that solves equations or
processes text.

The Gemini API provides code execution as a tool, similar to
[function calling](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/function-calling). After
you add code execution as a tool, the model decides when to use it.

## Supported models

| Model | Version |
| --- | --- |
| Gemini 2.0 Flash | `gemini-2.0-flash-001` |

### Limitations

- The feature doesn't support file I/O.
- Code execution can run for a maximum of 30 seconds before timing out.

## Example syntax

### curl

```
PROJECT_ID = myproject
REGION = us-central1
MODEL_ID = gemini-2.0-flash-001

https://${REGION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${REGION}/publishers/google/models/${MODEL_ID}:generateContent \\
  -d '{
    \"contents\": [{\\
      ...\\
    }],
    \"tools\": [{\\
      \"code_execution\":  {}\\
    }]
  }'
```

### Python

```
from google import genai
from google.genai.types import Tool, ToolCodeExecution, GenerateContentConfig

client = genai.Client()
model_id = \"gemini-2.0-flash-001\"

code_execution_tool = Tool(
    code_execution=ToolCodeExecution()
)
response = client.models.generate_content(
    model=model_id,
    contents=\"Calculate 20th fibonacci number. Then find the nearest palindrome to it.\",
    config=GenerateContentConfig(
        tools=[code_execution_tool],
        temperature=0,
    ),
)
```

## Parameter list

See [examples](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/code-execution-api#examples) for implementation details.

### Python

To enable code execution, specify a code execution `tool` in your request.

#### `CodeExecution`

Tool that executes code generated by the model, and automatically returns the result to the model. See also [ExecutableCode](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/code-execution-api#executablecode) and [CodeExecutionResult](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/code-execution-api#codeexecutionresult) which are input and output to this tool.

#### `Part`

|     |     |
| --- | --- |
| `executable_code` | Optional:<br>`ExecutableCode`<br>Code generated by the model that is meant to be executed.<br> <br>See Code Execution \$$API\$$. |
| `code_execution_result` | Optional:<br>`CodeExecutionResult`<br>Result of executing the \$$ExecutableCode\$$.<br> <br>See Code Execution \$$API\$$. |

#### `ExecutableCode`

|     |     |
| --- | --- |
| `language` | Required:<br>`string (enum)`<br>Supported programming languages for the generated `code`.<br> <br>Supported:<br> <br>- `PYTHON` |
| `code` | Required:<br>`string`<br>The code to be executed.<br> <br>See Code Execution \$$API\$$. |

#### `CodeExecutionResult`

|     |     |
| --- | --- |
| `outcome` | Required:<br>`string (enum)`<br>Outcome of the code execution.<br> <br>Possible outcomes:<br> <br>- Code execution completed successfully. ( `OUTCOME_OK`)<br>   <br>- Code execution finished but with a failure. `stderr` should contain the reason. ( `OUTCOME_FAILED`)<br>   <br>- Code execution ran for too long, and was cancelled. There may or may not be a partial output present. ( `OUTCOME_DEADLINE_EXCEEDED`) |
| `output` | Required:<br>`string`<br>Contains `stdout` when code execution is successful, `stderr` or other description otherwise.<br> <br>See Code Execution \$$API\$$. |

## Examples

Here are illustrations of how you can submit a query and function declarations to the model.

### Basic use case

### curl

```
PROJECT_ID = myproject
REGION = us-central1
MODEL_ID = gemini-2.0-flash-001

curl -X POST \\
  -H \"Authorization: Bearer $(gcloud auth print-access-token)\" \\
  -H \"Content-Type: application/json\" \\
  https://${REGION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${REGION}/publishers/google/models/${MODEL_ID}:generateContent \\
  -d '{
    \"contents\": [{\\
      \"role\": \"user\",\\
      \"parts\": [{\\
        \"text\": \"Calculate 20th fibonacci number. Then find the nearest palindrome to it.\"\
      }]\\
    }],
    \"tools\": [{'codeExecution': {}}],
  }'
```

### Python

```
from google import genai
from google.genai.types import Tool, ToolCodeExecution, GenerateContentConfig

client = genai.Client()
model_id = \"gemini-2.0-flash-001\"

code_execution_tool = Tool(
    code_execution=ToolCodeExecution()
)
response = client.models.generate_content(
    model=model_id,
    contents=\"Calculate 20th fibonacci number. Then find the nearest palindrome to it.\",
    config=GenerateContentConfig(
        tools=[code_execution_tool],
        temperature=0,
    ),
)
for part in response.candidates[0].content.parts:
    if part.executable_code:
        print(part.executable_code)
    if part.code_execution_result:
        print(part.code_execution_result)
# Example response:
# code='...' language='PYTHON'
# outcome='OUTCOME_OK' output='The 20th Fibonacci number is: 6765\\n'
# code='...' language='PYTHON'
# outcome='OUTCOME_OK' output='Lower Palindrome: 6666\\nHigher Palindrome: 6776\\nNearest Palindrome to 6765: 6776\\n'
```

### Enable code execution on the model

To enable basic code execution, see [Code execution](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/code-execution#enable_code_execution_on_the_model).

## What's next

- Learn more about the [Gemini\\
API](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/gemini).
- Learn more about [Function\\
calling](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling).
- Learn more about [Generating content with Gemini](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference).

 Send feedback

Except as otherwise noted, the content of this page is licensed under the [Creative Commons Attribution 4.0 License](https://creativecommons.org/licenses/by/4.0/), and code samples are licensed under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0). For details, see the [Google Developers Site Policies](https://developers.google.com/site-policies). Java is a registered trademark of Oracle and/or its affiliates.

Last updated 2025-04-12 UTC.
```

**5. URL: https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation**

```markdown
[Skip to main content](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation#main-content)

[![Google Cloud](https://www.gstatic.com/devrel-devsite/prod/vd31e3ed8994e05c7f2cd0cf68a402ca7902bb92b6ec0977d7ef2a1c699fae3f9/cloud/images/cloud-logo.svg)](https://cloud.google.com/)

`/`

- [English](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation)
- [Deutsch](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation?hl=de)
- [Español – América Latina](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation?hl=es-419)
- [Français](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation?hl=fr)
- [Indonesia](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation?hl=id)
- [Italiano](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation?hl=it)
- [Português – Brasil](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation?hl=pt-br)
- [中文 – 简体](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation?hl=zh-cn)
- [日本語](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation?hl=ja)
- [한국어](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation?hl=ko)

[Console](https://console.cloud.google.com/)

[Sign in](https://cloud.google.com/_d/signin?continue=https%3A%2F%2Fcloud.google.com%2Fvertex-ai%2Fgenerative-ai%2Fdocs%2Fmultimodal-response-generation&prompt=select_account)

- [Generative AI on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/overview)

[Contact Us](https://cloud.google.com/contact) [Start free](https://console.cloud.google.com/freetrial)

- On this page
- [Text generation](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation#text-generation)
- [Speech generation (private experimental)](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation#speech-generation)
  - [Generate speech](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation#use-speech-generation)
  - [Using Vertex AI Studio](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation#speech-gen-vertex-ai-studio)
  - [Using the API](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation#speech-gen-api)
- [Image generation (public experimental)](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation#image-generation)
  - [Generate images](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation#use-image-generation)
  - [Using Vertex AI Studio](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation#image-gen-vertex-ai-studio)
  - [Using the API](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation#image-gen-api)

- [Home](https://cloud.google.com/)
- [Generative AI on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/overview)
- [Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/overview)

Was this helpful?

 Send feedback

# Multimodal responses    bookmark_borderbookmark   Stay organized with collections     Save and categorize content based on your preferences.

- On this page
- [Text generation](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation#text-generation)
- [Speech generation (private experimental)](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation#speech-generation)
  - [Generate speech](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation#use-speech-generation)
  - [Using Vertex AI Studio](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation#speech-gen-vertex-ai-studio)
  - [Using the API](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation#speech-gen-api)
- [Image generation (public experimental)](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation#image-generation)
  - [Generate images](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation#use-image-generation)
  - [Using Vertex AI Studio](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation#image-gen-vertex-ai-studio)
  - [Using the API](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation#image-gen-api)

Gemini 2.0 Flash supports response generation in multiple modalities, including
text, speech, and images.

## Text generation

Gemini 2.0 Flash supports text generation using the Google Cloud console,
REST API, and supported SDKs. For more information, see our [text generation guide](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/send-chat-prompts-gemini).

## Speech generation (private experimental)

Gemini 2.0 supports a new multimodal generation capability: text to speech.
Using the text-to-speech capability, you can prompt the model to generate high
quality audio output that sounds like a human voice ( `say \"hi everyone\"`), and
you can further refine the output by steering the voice.

### Generate speech

The following sections cover how to generate speech using either [Vertex AI Studio](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation#speech-gen-vertex-ai-studio) or using [the\\
API](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation#speech-gen-api).

For guidance and best practices for prompting, see [Design multimodal\\
prompts](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/design-multimodal-prompts#fundamentals).

**Using Vertex AI Studio**

To use speech generation:

1. Open [**Vertex AI Studio > Create prompt**](https://console.cloud.google.com/vertex-ai/studio/multimodal).

2. Click **Switch model** and select **`gemini-2.0-flash-exp`**
    from the menu.

3. In the **Outputs** panel, select **Audio** from the
    drop-down menu.

4. Write a description of the speech you want to generate in the text area of
    the **Write a prompt** text area.

5. Click the **Prompt** (send) button.

Gemini will generate speech based on your description. This
process should take a few seconds, but may be comparatively slower depending on
capacity.\\*

**Using the API**

Save the request body in a file named `request.json`.
Run the following command in the terminal to create or overwrite this file in
the current directory:

See more code actions.

Light code theme

Dark code theme

```
cat << EOF > request.json
{
  \"contents\": [\\
    {\\
      \"role\": \"user\",\\
      \"parts\": [\\
        { \"text\": \"Say, 'How are you?'\" }\\
      ]\\
    }\\
  ],
  \"generation_config\": {
    \"response_modalities\": [\\
      \"AUDIO\"\"\\
    ]
  },
  \"safety_settings\": [\\
    {\\
      \"category\": \"HARM_CATEGORY_HATE_SPEECH\",\\
      \"threshold\": \"BLOCK_NONE\"\\
    },\\
    {\\
      \"category\": \"HARM_CATEGORY_DANGEROUS_CONTENT\",\\
      \"threshold\": \"BLOCK_NONE\"\\
    },\\
    {\\
      \"category\": \"HARM_CATEGORY_HARASSMENT\",\\
      \"threshold\": \"BLOCK_NONE\"\\
    },\\
    {\\
      \"category\":\\
      \"HARM_CATEGORY_SEXUALLY_EXPLICIT\",\\
      \"threshold\": \"BLOCK_NONE\"\\
    }\\
  ]
}
EOF
```

Then execute the following command to send your REST request:

See more code actions.

Light code theme

Dark code theme

```
curl -X POST \\
     -H \"Authorization: Bearer $(gcloud auth print-access-token)\" \\
     -H \"Content-Type: application/json; charset=utf-8\" \\
     \"https://us-central1-aiplatform.googleapis.com/v1/projects/PROJECT_ID/locations/us-central1/publishers/google/models/gemini-2.0-flash-exp:generateContent\" \\
     -d $\"@request.json\"
```

Gemini will generate audio based on your description. This
process should take a few seconds, but may be comparatively slower depending on
capacity.

## Image generation (public experimental)

Gemini 2.0 Flash Experimental Image Generation ( `gemini-2.0-flash-exp`) supports
the ability to generate images in addition to text. This expands Gemini's
capabilities to include the following:

- Iteratively generate images through conversation with natural language,
adjusting images while maintaining consistency and context.
- Generate images with high-quality long text rendering.
- Generate interleaved text-image output. For example, a blog post with
text and images in a single turn. Previously, this required stringing
together multiple models.
- Generate images using Gemini's world knowledge and reasoning capabilities.

With this public experimental release, Gemini 2.0 Flash Experimental Image
Generation can generate images in 1024px, supports generating and editing
images of people, and contains updated safety filters that provide a more
flexible and less restrictive user experience.

It supports the following modalities and capabilities:

- Text to image

  - **Example prompt:** \"Generate an image of the Eiffel tower with
    fireworks in the background.\"
- Text to image (text rendering)

  - **Example prompt:** \"generate a cinematic photo of a large
    building with this giant text projection mapped on the front of the
    building: \"Gemini 2.0 can now generate long form text\"\"
- Text to image(s) and text (interleaved)

  - **Example prompt:** \"Generate an illustrated recipe for a
    paella. Create images alongside the text as you generate the recipe.\"
  - **Example prompt:** \"Generate a story about a dog in a 3D
    cartoon animation style. For each scene, generate an image\"
- Image(s) and text to image(s) and text (interleaved)

  - **Example prompt:** (With an image of a furnished room) \"What
    other color sofas would work in my space? Can you update the image?\"
- Image editing (text and image to image)

  - **Example prompt:** \"Edit this image to make it look like a cartoon\"
  - **Example prompt:** \$$image of a cat\$$ + \$$image of a pillow\$$ +
    \"Create a cross stitch of my cat on this pillow.\"
- Multi-turn image editing (chat)

  - **Example prompts:** \$$upload an image of a blue car.\$$ \"Turn
    this car into a convertible.\" \"Now change the color to yellow.\"

**Limitations:**

- For best performance, use the following languages: EN, es-MX, ja-JP,
zh-CN, hi-IN.
- Image generation does not support audio or video inputs.
- Image generation may not always trigger:
  - The model may output text only. Try asking for image outputs
    explicitly. For example, \"provide images as you go along.\"
  - The model may generate text as an image. Try asking for text
    outputs explicitly. For example, \"generate narrative text along with
    illustrations.\"
  - The model may stop generating partway through. Try again or try
    a different prompt.

### Generate images

The following sections cover how to generate images using either [Vertex AI Studio](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation#image-gen-vertex-ai-studio) or using [the\\
API](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal-response-generation#image-gen-api).

For guidance and best practices for prompting, see [Design multimodal\\
prompts](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/design-multimodal-prompts#fundamentals).

**Using Vertex AI Studio**

To use image generation:

1. Open [**Vertex AI Studio > Create prompt**](https://console.cloud.google.com/vertex-ai/studio/multimodal).

2. Click **Switch model** and select **`gemini-2.0-flash-exp`**
    from the menu.

3. In the **Outputs** panel, select **Image and text** from the
    drop-down menu.

4. Write a description of the image you want to generate in the text area of
    the **Write a prompt** text area.

5. Click the **Prompt** (send) button.

Gemini will generate an image based on your description. This
process should take a few seconds, but may be comparatively slower depending on
capacity.

**Using the API**

Save the request body in a file named `request.json`.
Run the following command in the terminal to create or overwrite this file in
the current directory:

See more code actions.

Light code theme

Dark code theme

```
cat << EOF > request.json
{
  \"contents\": [\\
    {\\
      \"role\": \"user\",\\
      \"parts\": [\\
        { \"text\": \"Generate an image of a cat.\" }\\
      ]\\
    }\\
  ],
  \"generation_config\": {
    \"response_modalities\": [\\
      \"IMAGE\", \"TEXT\"\\
    ]
  },
  \"safety_settings\": [\\
    {\\
      \"category\": \"HARM_CATEGORY_HATE_SPEECH\",\\
      \"threshold\": \"BLOCK_NONE\"\\
    },\\
    {\\
      \"category\": \"HARM_CATEGORY_DANGEROUS_CONTENT\",\\
      \"threshold\": \"BLOCK_NONE\"\\
    },\\
    {\\
      \"category\": \"HARM_CATEGORY_HARASSMENT\",\\
      \"threshold\": \"BLOCK_NONE\"\\
    },\\
    {\\
      \"category\":\\
      \"HARM_CATEGORY_SEXUALLY_EXPLICIT\",\\
      \"threshold\": \"BLOCK_NONE\"\\
    }\\
  ]
}
EOF
```

Then execute the following command to send your REST request:

See more code actions.

Light code theme

Dark code theme

```
curl -X POST \\
     -H \"Authorization: Bearer $(gcloud auth print-access-token)\" \\
     -H \"Content-Type: application/json; charset=utf-8\" \\
     \"https://us-central1-aiplatform.googleapis.com/v1/projects/PROJECT_ID/locations/us-central1/publishers/google/models/gemini-2.0-flash-exp:generateContent\" \\
     -d $\"@request.json\"
```

Gemini will generate an image based on your description. This
process should take a few seconds, but may be comparatively slower depending on
capacity.

Was this helpful?

 Send feedback

Except as otherwise noted, the content of this page is licensed under the [Creative Commons Attribution 4.0 License](https://creativecommons.org/licenses/by/4.0/), and code samples are licensed under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0). For details, see the [Google Developers Site Policies](https://developers.google.com/site-policies). Java is a registered trademark of Oracle and/or its affiliates.

Last updated 2025-04-12 UTC.

[iframe](https://feedback-pa.clients6.google.com/static/proxy.html?usegapi=1&jsh=m%3B%2F_%2Fscs%2Fabc-static%2F_%2Fjs%2Fk%3Dgapi.lb.en.fwXSHnIYz-4.O%2Fd%3D1%2Frs%3DAHpOoo_SvulQ5pP6FvvJyrQeIOJ4MStGTQ%2Fm%3D__features__#parent=https%3A%2F%2Fcloud.google.com&rpctoken=294966354)[iframe](https://scone-pa.clients6.google.com/static/proxy.html?usegapi=1&jsh=m%3B%2F_%2Fscs%2Fabc-static%2F_%2Fjs%2Fk%3Dgapi.lb.en.fwXSHnIYz-4.O%2Fd%3D1%2Frs%3DAHpOoo_SvulQ5pP6FvvJyrQeIOJ4MStGTQ%2Fm%3D__features__#parent=https%3A%2F%2Fcloud.google.com&rpctoken=567865942)
```

**6. URL: https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding**

```markdown
[Skip to main content](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding#main-content)

[![Google Cloud](https://www.gstatic.com/devrel-devsite/prod/vd31e3ed8994e05c7f2cd0cf68a402ca7902bb92b6ec0977d7ef2a1c699fae3f9/cloud/images/cloud-logo.svg)](https://cloud.google.com/)

`/`

- [English](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding)
- [Deutsch](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding?hl=de)
- [Español – América Latina](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding?hl=es-419)
- [Français](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding?hl=fr)
- [Indonesia](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding?hl=id)
- [Italiano](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding?hl=it)
- [Português – Brasil](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding?hl=pt-br)
- [中文 – 简体](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding?hl=zh-cn)
- [日本語](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding?hl=ja)
- [한국어](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding?hl=ko)

[Console](https://console.cloud.google.com/)

[Sign in](https://cloud.google.com/_d/signin?continue=https%3A%2F%2Fcloud.google.com%2Fvertex-ai%2Fgenerative-ai%2Fdocs%2Fmultimodal%2Fdocument-understanding&prompt=select_account)

- [Generative AI on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/overview)

[Contact Us](https://cloud.google.com/contact) [Start free](https://console.cloud.google.com/freetrial)

- On this page
- [Supported models](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding#supported_models)
- [Add documents to a request](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding#add_documents_to_a_request)
- [Set optional model parameters](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding#set-optional-model-parameters)
- [Document requirements](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding#document-requirements)
- [PDF best practices](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding#best-practices)
- [Limitations](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding#limitations)
- [What's next](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding#whats_next)

- [Home](https://cloud.google.com/)
- [Generative AI on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/overview)
- [Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/overview)

 Send feedback

# Document understanding    bookmark_borderbookmark   Stay organized with collections     Save and categorize content based on your preferences.

Release Notes

- On this page
- [Supported models](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding#supported_models)
- [Add documents to a request](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding#add_documents_to_a_request)
- [Set optional model parameters](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding#set-optional-model-parameters)
- [Document requirements](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding#document-requirements)
- [PDF best practices](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding#best-practices)
- [Limitations](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding#limitations)
- [What's next](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding#whats_next)

You can add documents (PDF and TXT files) to Gemini requests to
perform tasks that involve understanding the contents of the included documents.
This page shows you how to add PDFs to your requests to Gemini in
Vertex AI by using the Google Cloud console and the Vertex AI API.

## Supported models

The following table lists the models that support document understanding:

| **Model** | **Document modality details** | **Try the model** |
| --- | --- | --- |
| [Gemini 2.0 Flash](https://console.cloud.google.com/vertex-ai/publishers/google/model-garden/gemini-2.0-flash-001)<br>`gemini-2.0-flash` | - Maximum number of files per request: 3,000<br>- Maximum number of pages per file: 1,000<br>- Maximum file size per file: 50 MB<br>- Maximum tokens per minute (TPM) per project1:<br>  - High/Medium/Default media resolution:<br>    - **US/Asia**: 670 K<br>    - **EU**: 168 K<br>  - Low media resolution:<br>    - **US/Asia**: 179 K<br>    - **EU**: 45 K | [Try Gemini 2.0 Flash](https://console.cloud.google.com/vertex-ai/generative/multimodal/create/text?model=gemini-2.0-flash-001) |
| [Gemini 2.0 Flash-Lite](https://console.cloud.google.com/vertex-ai/publishers/google/model-garden/gemini-2.0-flash-lite-001)<br>`gemini-2.0-flash-lite` | - Maximum number of files per request: 3,000<br>- Maximum number of pages per file: 1,000<br>- Maximum file size per file: 50 MB<br>- Maximum tokens per minute (TPM):<br>  - High/Medium/Default media resolution:<br>    - **US/Asia**: 3.4 M<br>    - **EU**: 839 K<br>  - Low media resolution:<br>    - **US/Asia**: 3.4 M<br>    - **EU**: 839 K | [Try Gemini 2.0 Flash-Lite](https://console.cloud.google.com/vertex-ai/generative/multimodal/create/text?model=gemini-2.0-flash-lite-001) |

1This is the maximum TPM from document inputs across all requests of
a project. Also use the maximum TPM for other modalities.

The quota metric is
`generate_content_document_input_per_base_model_id_and_resolution`.

For a list of languages supported by Gemini models, see model information
[Google models](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/models). To learn
more about how to design multimodal prompts, see
[Design multimodal prompts](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/design-multimodal-prompts).
If you're looking for a way to use Gemini directly from your mobile and
web apps, see the
[Vertex AI in Firebase SDKs](https://firebase.google.com/docs/vertex-ai) for
Android, Swift, web, and Flutter apps.

## Add documents to a request

The following code sample shows you how to include a PDF in a prompt request.
This PDF sample works with all Gemini multimodal models.

[Gen AI SDK for Python](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding#gen-ai-sdk-for-python)[REST](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding#rest)[Console](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding#console)More

#### Install

```
pip install --upgrade google-genai
```

To learn more, see the
[SDK reference documentation](https://googleapis.github.io/python-genai/).

Set environment variables to use the Gen AI SDK with Vertex AI:

```
# Replace the `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` values
# with appropriate values for your project.
export GOOGLE_CLOUD_PROJECT=GOOGLE_CLOUD_PROJECT
export GOOGLE_CLOUD_LOCATION=us-central1
export GOOGLE_GENAI_USE_VERTEXAI=True
```

```
from google import genai
from google.genai.types import HttpOptions, Part

client = genai.Client(http_options=HttpOptions(api_version=\"v1\"))
model_id = \"gemini-2.0-flash-001\"

prompt = \"\"\"
You are a highly skilled document summarization specialist.
Your task is to provide a concise executive summary of no more than 300 words.
Please summarize the given document for a general audience.
\"\"\"

pdf_file = Part.from_uri(
    file_uri=\"gs://cloud-samples-data/generative-ai/pdf/1706.03762v7.pdf\",
    mime_type=\"application/pdf\",
)

response = client.models.generate_content(
    model=model_id,
    contents=[pdf_file, prompt],
)

print(response.text)
# Example response:
# Here is a summary of the document in 300 words.
#
# The paper introduces the Transformer, a novel neural network architecture for
# sequence transduction tasks like machine translation. Unlike existing models that rely on recurrent or
# convolutional layers, the Transformer is based entirely on attention mechanisms.
# ...
```

After you
[set up your environment](https://cloud.google.com/vertex-ai/generative-ai/docs/start/quickstarts/quickstart-multimodal#gemini-setup-environment-drest),
you can use REST to test a text prompt. The following sample sends a request to the publisher
model endpoint.

Before using any of the request data,
make the following replacements:

- `LOCATION`: The region to process the
request.
Enter a supported region. For the full list of supported regions, see
[Available locations](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/locations#available-regions).

**Click to expand a partial list of available regions**

- `us-central1`
- `us-west4`
- `northamerica-northeast1`
- `us-east4`
- `us-west1`
- `asia-northeast3`
- `asia-southeast1`
- `asia-northeast1`

- `PROJECT_ID`: Your [project ID](https://cloud.google.com/resource-manager/docs/creating-managing-projects#identifiers).
- `FILE_URI`:
The URI or URL of the file to include in the prompt. Acceptable values include the following:

  - **Cloud Storage bucket URI:** The object must either be publicly readable or reside in
     the same Google Cloud project that's sending the request. For `gemini-2.0-flash`
     and `gemini-2.0-flash-lite`, the size limit is 2 GB.
  - **HTTP URL:** The file URL must be publicly readable. You can specify one video file, one
     audio file, and up to 10 image files per request. Audio files, video files, and documents can't
     exceed 15 MB.
  - **YouTube video URL:** The YouTube video must be either owned by the account that you used
     to sign in to the Google Cloud console or is public. Only one YouTube video URL is supported per
     request.

When specifying a `fileURI`, you must also specify the media type
( `mimeType`) of the file. If VPC Service Controls is enabled, specifying a media file
URL for `fileURI` is not supported.

If you don't have a PDF file in Cloud Storage, then you can use the following
publicly available file:
`gs://cloud-samples-data/generative-ai/pdf/2403.05530.pdf` with a mime type of
`application/pdf`. To view this PDF,
[open the sample PDF](https://storage.googleapis.com/cloud-samples-data/generative-ai/pdf/2403.05530.pdf)
file.

- `MIME_TYPE`:
The media type of the file specified in the `data` or `fileUri`
fields. Acceptable values include the following:

**Click to expand MIME types**

- `application/pdf`
- `audio/mpeg`
- `audio/mp3`
- `audio/wav`
- `image/png`
- `image/jpeg`
- `image/webp`
- `text/plain`
- `video/mov`
- `video/mpeg`
- `video/mp4`
- `video/mpg`
- `video/avi`
- `video/wmv`
- `video/mpegps`
- `video/flv`

- `TEXT`:
The text instructions to include in the prompt.
For example,
`You are a very professional document summarization specialist. Please summarize the given
        document.`

To send your request, choose one of these options:

[curl](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding#curl)[PowerShell](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding#powershell)More

Save the request body in a file named `request.json`.
Run the following command in the terminal to create or overwrite
this file in the current directory:

```
cat > request.json << 'EOF'
{
  \"contents\": {
    \"role\": \"USER\",
    \"parts\": [\\
      {\\
        \"fileData\": {\\
          \"fileUri\": \"FILE_URI\",\\
          \"mimeType\": \"MIME_TYPE\"\\
        }\\
      },\\
      {\\
        \"text\": \"TEXT\"\\
      }\\
    ]
  }
}
EOF
```

Then execute the following command to send your REST request:

```
curl -X POST \\
     -H \"Authorization: Bearer $(gcloud auth print-access-token)\" \\
     -H \"Content-Type: application/json; charset=utf-8\" \\
     -d @request.json \\
     \"https://LOCATION-aiplatform.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/publishers/google/models/gemini-2.0-flash:generateContent\"
```

Save the request body in a file named `request.json`.
Run the following command in the terminal to create or overwrite
this file in the current directory:

```
@'
{
  \"contents\": {
    \"role\": \"USER\",
    \"parts\": [\\
      {\\
        \"fileData\": {\\
          \"fileUri\": \"FILE_URI\",\\
          \"mimeType\": \"MIME_TYPE\"\\
        }\\
      },\\
      {\\
        \"text\": \"TEXT\"\\
      }\\
    ]
  }
}
'@  | Out-File -FilePath request.json -Encoding utf8
```

Then execute the following command to send your REST request:

```
$cred = gcloud auth print-access-token
$headers = @{ \"Authorization\" = \"Bearer $cred\" }

Invoke-WebRequest `
    -Method POST `
    -Headers $headers `
    -ContentType: \"application/json; charset=utf-8\" `
    -InFile request.json `
    -Uri \"https://LOCATION-aiplatform.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/publishers/google/models/gemini-2.0-flash:generateContent\" | Select-Object -Expand Content
```

You should receive a JSON response similar to the following.

**Response**

```
{
  \"candidates\": [\\
    {\\
      \"content\": {\\
        \"role\": \"model\",\\
        \"parts\": [\\
          {\\
            \"text\": \"This report presents Gemini 2.0 Pro.\\n\"\\
          }\\
        ]\\
      },\\
      \"finishReason\": \"STOP\",\\
      \"safetyRatings\": [\\
        {\\
          \"category\": \"HARM_CATEGORY_HATE_SPEECH\",\\
          \"probability\": \"NEGLIGIBLE\",\\
          \"probabilityScore\": 0.13273923,\\
          \"severity\": \"HARM_SEVERITY_NEGLIGIBLE\",\\
          \"severityScore\": 0.08819004\\
        },\\
        {\\
          \"category\": \"HARM_CATEGORY_DANGEROUS_CONTENT\",\\
          \"probability\": \"NEGLIGIBLE\",\\
          \"probabilityScore\": 0.1046602,\\
          \"severity\": \"HARM_SEVERITY_NEGLIGIBLE\",\\
          \"severityScore\": 0.0996453\\
        },\\
        {\\
          \"category\": \"HARM_CATEGORY_HARASSMENT\",\\
          \"probability\": \"NEGLIGIBLE\",\\
          \"probabilityScore\": 0.15987214,\\
          \"severity\": \"HARM_SEVERITY_NEGLIGIBLE\",\\
          \"severityScore\": 0.098946586\\
        },\\
        {\\
          \"category\": \"HARM_CATEGORY_SEXUALLY_EXPLICIT\",\\
          \"probability\": \"NEGLIGIBLE\",\\
          \"probabilityScore\": 0.056966383,\\
          \"severity\": \"HARM_SEVERITY_NEGLIGIBLE\",\\
          \"severityScore\": 0.075721376\\
        }\\
      ]\\
    }\\
  ],
  \"usageMetadata\": {
    \"promptTokenCount\": 19882,
    \"candidatesTokenCount\": 336,
    \"totalTokenCount\": 20218
  }
}

```

Note the following in the URL for this sample:

- Use the
[`generateContent`](https://cloud.google.com/vertex-ai/docs/reference/rest/v1/projects.locations.publishers.models/generateContent)
method to request that the response is returned after it's fully generated.
To reduce the perception of latency to a human audience, stream the response as it's being
generated by using the
[`streamGenerateContent`](https://cloud.google.com/vertex-ai/docs/reference/rest/v1/projects.locations.publishers.models/streamGenerateContent)
method.

- The multimodal model ID is located at the end of the URL before the method
(for example, `gemini-2.0-flash`). This sample might support other
models as well.

To send a multimodal prompt by using the Google Cloud console, do the
following:

01. In the Vertex AI section of the Google Cloud console, go to
     the **Vertex AI Studio** page.

    [Go to Vertex AI Studio](https://console.cloud.google.com/vertex-ai/generative/multimodal)

02. Click **Create prompt**.

03. Optional: Configure the model and parameters:

    - **Model**: Select a model.
04. Optional: To configure advanced parameters, click **Advanced** and
     configure as follows:

    **Click to expand advanced configurations**

- **Top-K**: Use the slider or textbox to enter a value for top-K.

Top-K changes how the model selects tokens for output. A top-K of
`1` means the next selected token is the most probable among all
tokens in the model's vocabulary (also called greedy decoding), while a top-K of
`3` means that the next token is selected from among the three most
probable tokens by using temperature.

For each token selection step, the top-K tokens with the highest
probabilities are sampled. Then tokens are further filtered based on top-P with
the final token selected using temperature sampling.

Specify a lower value for less random responses and a higher value for more
random responses.

- **Top-P**: Use the slider or textbox to enter a value for top-P.
Tokens are selected from most probable to the least until the sum of their
probabilities equals the value of top-P. For the least variable results,
set top-P to `0`.
- **Max responses**: Use the slider or textbox to enter a value for
the number of responses to generate.
- **Streaming responses**: Enable to print responses as they're
generated.
- **Safety filter threshold**: Select the threshold of how likely you
are to see responses that could be harmful.
- **Enable Grounding**: Grounding isn't supported for multimodal
prompts.
- **Region**: Select the region that you want to use.
- **Temperature**: Use the slider or textbox to enter a value for
temperature.

```

The temperature is used for sampling during response generation, which occurs when topP
and topK are applied. Temperature controls the degree of randomness in token selection.
Lower temperatures are good for prompts that require a less open-ended or creative response, while
higher temperatures can lead to more diverse or creative results. A temperature of 0
means that the highest probability tokens are always selected. In this case, responses for a given
prompt are mostly deterministic, but a small amount of variation is still possible.

If the model returns a response that's too generic, too short, or the model gives a fallback
response, try increasing the temperature.
</li>
    <li>**Output token limit**: Use the slider or textbox to enter a value for
      the max output limit.

Maximum number of tokens that can be generated in the response. A token is
approximately four characters. 100 tokens correspond to roughly 60-80 words.

Specify a lower value for shorter responses and a higher value for potentially longer
responses.
</li>
    <li>**Add stop sequence**: Optional. Enter a stop sequence, which is a
      series of characters that includes spaces. If the model encounters a
      stop sequence, the response generation stops. The stop sequence isn't
      included in the response, and you can add up to five stop sequences.</li>
</ul>

```

05. Click **Insert Media**, and select a source for your file.

    [Upload](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding#upload)[By URL](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding#by-url)[Cloud Storage](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding#cloud-storage)[Google Drive](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/document-understanding#google-drive)More

    Select the file that you want to upload and click **Open**.

    Enter the URL of the file that you want to use and click **Insert**.

    Select the bucket and then the file from the bucket that
    you want to import and click **Select**.

1. Choose an account and give consent to
Vertex AI Studio to access your account the first
time you select this option. You can upload multiple files that
have a total size of up to 10 MB. A single file can't exceed
7 MB.
2. Click the file that you want to add.
3. Click **Select**.

The file thumbnail displays in the **Prompt** pane. The total
number of tokens also displays. If your prompt data exceeds the
[token limit](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/models#gemini-models), the
tokens are truncated and aren't included in processing your data.

06. Enter your text prompt in the **Prompt** pane.

07. Optional: To view the **Token ID to text** and **Token IDs**, click the
     **tokens count** in the **Prompt** pane.

08. Click **Submit**.

09. Optional: To save your prompt to **My prompts**, click save_alt **Save**.

10. Optional: To get the Python code or a curl command for your prompt, click
     code **Build with code > Get code**.

## Set optional model parameters

Each model has a set of optional parameters that you can set. For more
information, see [Content generation parameters](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/content-generation-parameters).

## Document requirements

Gemini multimodal models support the following document MIME types:

| Document MIME type | Gemini 2.0 Flash | Gemini 2.0 Flash-Lite |
| --- | --- | --- |
| PDF - `application/pdf` |  |  |
| Text - `text/plain` |  |  |

PDFs are treated as images, so a single page of a PDF is treated as one
image. The number of pages allowed in a prompt is limited to the number of
images the model can support:

- **Gemini 2.0 Flash and Gemini 2.0 Flash-Lite**:

  - Maximum files per request: 3,000
  - Maximum pages per file: 1,000
  - Maximum size per file: 50 MB

**PDF tokenization**

PDFs are treated as images, so each page of a PDF is tokenized in the same
way as an image.

Also, the cost for PDFs follows
[Gemini image pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing#gemini-models).
For example, if you include a two-page PDF in a Gemini API call, you
incur an input fee of processing two images.

**Plain text tokenization**

Plain text documents are tokenized as text. For example, if you include a 100-word plain text
document in a Gemini API call, you incur an input fee of processing 100 words.

## PDF best practices

When using PDFs, use the following best practices and information for the
best results:

- If your prompt contains a single PDF, place the PDF before the text
prompt in your request.

- If you have a long document, consider splitting it into multiple PDFs
to process it.

- Use PDFs created with text rendered as text instead of using text in
scanned images. This format ensures text is machine-readable so that it's
easier for the model to edit, search, and manipulate compared to scanned
image PDFs. This practice provides optimal results when working with
text-heavy documents like contracts.

## Limitations

While Gemini multimodal models are powerful in many multimodal use
cases, it's important to understand the limitations of the models:

- **Spatial reasoning**: The models aren't precise at locating
text or objects in PDFs. They might only return the approximated counts of
objects.

- **Accuracy**: The models might hallucinate when interpreting
handwritten text in PDF documents.

## What's next

- Start building with Gemini multimodal models - new customers [get $300 in free Google Cloud credits](https://console.cloud.google.com/freetrial?redirectPath=/vertex-ai/model-garden) to explore what they can do with Gemini.
- Learn how to [send chat prompt requests](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/send-chat-prompts-gemini).
- Learn about [responsible AI best practices and Vertex AI's safety filters](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/responsible-ai).

 Send feedback

Except as otherwise noted, the content of this page is licensed under the [Creative Commons Attribution 4.0 License](https://creativecommons.org/licenses/by/4.0/), and code samples are licensed under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0). For details, see the [Google Developers Site Policies](https://developers.google.com/site-policies). Java is a registered trademark of Oracle and/or its affiliates.

Last updated 2025-04-12 UTC.

[iframe](https://feedback-pa.clients6.google.com/static/proxy.html?usegapi=1&jsh=m%3B%2F_%2Fscs%2Fabc-static%2F_%2Fjs%2Fk%3Dgapi.lb.en.fwXSHnIYz-4.O%2Fd%3D1%2Frs%3DAHpOoo_SvulQ5pP6FvvJyrQeIOJ4MStGTQ%2Fm%3D__features__#parent=https%3A%2F%2Fcloud.google.com&rpctoken=1453147730)
```

Okay, I have retrieved the content for the 5 URLs you requested. Here is the text from each page in Markdown format:

**7. URL: https://cloud.google.com/vertex-ai/generative-ai/docs/live-api**

```markdown
[Skip to main content](https://cloud.google.com/vertex-ai/generative-ai/docs/live-api#main-content)

[![Google Cloud](https://www.gstatic.com/devrel-devsite/prod/vd31e3ed8994e05c7f2cd0cf68a402ca7902bb92b6ec0977d7ef2a1c699fae3f9/cloud/images/cloud-logo.svg)](https://cloud.google.com/)

`/`

- English
- Deutsch
- Español – América Latina
- Français
- Indonesia
- Italiano
- Português – Brasil
- 中文 – 简体
- 日本語
- 한국어

[Console](https://console.cloud.google.com/)Sign in

- [Generative AI on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/overview)

[Contact Us](https://cloud.google.com/contact) [Start free](https://console.cloud.google.com/freetrial)

- [Home](https://cloud.google.com/)
- [Generative AI on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/overview)
- [Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/overview)

 Send feedback

# Gemini Live API       Stay organized with collections     Save and categorize content based on your preferences.

The Gemini Live API enables low-latency bidirectional voice and video
interactions with Gemini. Using the Live API, you can
provide end users with the experience of natural, human-like voice
conversations, and with the ability to interrupt the model's responses using
voice commands. The Live API
can process text, audio, and video input, and it can provide text and audio
output.

## Features

The Live API features the following technical specifications:

- **Inputs:** Text, audio, and video
- **Outputs:** Text and audio (synthesized speech)
- **Default session length:** 10 minutes

  - Session length can be extended in 10 minute increments as needed
- **Context window:** 32K tokens
- Selection between 8 voices for responses
- Support for responses in 31 languages

## Use the Live API

The following sections provide examples on how to use the
Live API's features.

For more information, see the [Gemini Live API reference\\
guide](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/multimodal-live).

### Send text and receive audio

#### Gen AI SDK for Python

```
voice_name = \"Aoede\"  # @param [\"Aoede\", \"Puck\", \"Charon\", \"Kore\", \"Fenrir\", \"Leda\", \"Orus\", \"Zephyr\"]

config = LiveConnectConfig(
    response_modalities=[\"AUDIO\"],
    speech_config=SpeechConfig(
        voice_config=VoiceConfig(
            prebuilt_voice_config=PrebuiltVoiceConfig(
                voice_name=voice_name,
            )
        ),
    ),
)

async with client.aio.live.connect(
    model=MODEL_ID,
    config=config,
) as session:
    text_input = \"Hello? Gemini are you there?\"
    display(Markdown(f\"**Input:** {text_input}\"))

    await session.send_client_content(
        turns=Content(role=\"user\", parts=[Part(text=text_input)]))

    audio_data = []
    async for message in session.receive():
        if (
            message.server_content.model_turn
            and message.server_content.model_turn.parts
        ):
            for part in message.server_content.model_turn.parts:
                if part.inline_data:
                    audio_data.append(
                        np.frombuffer(part.inline_data.data, dtype=np.int16)
                    )

    if audio_data:
        display(Audio(np.concatenate(audio_data), rate=24000, autoplay=True))

```

### Send and receive text

### Gen AI SDK for Python

#### Install

```
pip install --upgrade google-genai
```

To learn more, see the
[SDK reference documentation](https://googleapis.github.io/python-genai/).

Set environment variables to use the Gen AI SDK with Vertex AI:

```
# Replace the `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` values
# with appropriate values for your project.
export GOOGLE_CLOUD_PROJECT=GOOGLE_CLOUD_PROJECT
export GOOGLE_CLOUD_LOCATION=us-central1
export GOOGLE_GENAI_USE_VERTEXAI=True
```

```
from google import genai
from google.genai.types import (
    Content,
    LiveConnectConfig,
    HttpOptions,
    Modality,
    Part,
)

client = genai.Client(http_options=HttpOptions(api_version=\"v1beta1\"))
model_id = \"gemini-2.0-flash-live-preview-04-09\"

async with client.aio.live.connect(
    model=model_id,
    config=LiveConnectConfig(response_modalities=[Modality.TEXT]),
) as session:
    text_input = \"Hello? Gemini, are you there?\"
    print(\"> \", text_input, \"\\n\")
    await session.send_client_content(
        turns=Content(role=\"user\", parts=[Part(text=text_input)])
    )

    response = []

    async for message in session.receive():
        if message.text:
            response.append(message.text)

    print(\"\".join(response))
# Example output:
# >  Hello? Gemini, are you there?
# Yes, I'm here. What would you like to talk about?
```

### Send audio

#### Gen AI SDK for Python

```
import asyncio
import wave
from google import genai

client = genai.Client(api_key=\"GEMINI_API_KEY\", http_options={'api_version': 'v1alpha'})
model = \"gemini-2.0-flash-live-preview-04-09\"

config = {\"response_modalities\": [\"AUDIO\"]}

async def main():
    async with client.aio.live.connect(model=model, config=config) as session:
        wf = wave.open(\"audio.wav\", \"wb\")
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)

        message = \"Hello? Gemini are you there?\"
        await session.send_client_content(
            turns=Content(role=\"user\", parts=[Part(text=message)]))

        async for idx,response in async_enumerate(session.receive()):
            if response.data is not None:
                wf.writeframes(response.data)

            # Un-comment this code to print audio data info
            # if response.server_content.model_turn is not None:
            #      print(response.server_content.model_turn.parts[0].inline_data.mime_type)

        wf.close()

if __name__ == \"__main__\":
    asyncio.run(main())

```

The Live API supports the following audio formats:

- **Input audio format:** Raw 16 bit PCM audio at 16kHz little-endian
- **Output audio format:** Raw 16 bit PCM audio at 24kHz little-endian

### Audio transcription

The Live API can transcribe both input and output audio:

#### Gen AI SDK for Python

```
# Set model generation_config
CONFIG = {
    'response_modalities': ['AUDIO'],
}

headers = {
    \"Content-Type\": \"application/json\",
    \"Authorization\": f\"Bearer {bearer_token[0]}\",
}

# Connect to the server
async with connect(SERVICE_URL, additional_headers=headers) as ws:
    # Setup the session
    await ws.send(
        json.dumps(
            {
                \"setup\": {
                    \"model\": \"gemini-2.0-flash-live-preview-04-09\",
                    \"generation_config\": CONFIG,
                    'input_audio_transcription': {},
                    'output_audio_transcription': {}
                }
            }
        )
    )

    # Receive setup response
    raw_response = await ws.recv(decode=False)
    setup_response = json.loads(raw_response.decode(\"ascii\"))

    # Send text message
    text_input = \"Hello? Gemini are you there?\"
    display(Markdown(f\"**Input:** {text_input}\"))

    msg = {
        \"client_content\": {
            \"turns\": [{\"role\": \"user\", \"parts\": [{\"text\": text_input}]}],
            \"turn_complete\": True,
        }
    }

    await ws.send(json.dumps(msg))

    responses = []
    input_transcriptions = []
    output_transcriptions = []

    # Receive chucks of server response
    async for raw_response in ws:
        response = json.loads(raw_response.decode())
        server_content = response.pop(\"serverContent\", None)
        if server_content is None:
            break

        if (input_transcription := server_content.get(\"inputTranscription\")) is not None:
            if (text := input_transcription.get(\"text\")) is not None:
                input_transcriptions.append(text)
        if (output_transcription := server_content.get(\"outputTranscription\")) is not None:
            if (text := output_transcription.get(\"text\")) is not None:
                output_transcriptions.append(text)

        model_turn = server_content.pop(\"modelTurn\", None)
        if model_turn is not None:
            parts = model_turn.pop(\"parts\", None)
            if parts is not None:
                for part in parts:
                    pcm_data = base64.b64decode(part[\"inlineData\"][\"data\"])
                    responses.append(np.frombuffer(pcm_data, dtype=np.int16))

        # End of turn
        turn_complete = server_content.pop(\"turnComplete\", None)
        if turn_complete:
            break

    if input_transcriptions:
        display(Markdown(f\"**Input transcription >** {''.join(input_transcriptions)}\"))

    if responses:
        # Play the returned audio message
        display(Audio(np.concatenate(responses), rate=24000, autoplay=True))

    if output_transcriptions:
        display(Markdown(f\"**Output transcription >** {''.join(output_transcriptions)}\"))

```

### Change voice and language settings

The Live API uses Chirp 3 to support synthesized speech responses
in 8 HD voices and 31 languages.

You can select between the following voices:

- `Aoede` (female)
- `Charon` (male)
- `Fenrir` (male)
- `Kore` (female)
- `Leda` (female)
- `Orus` (male)
- `Puck` (male)
- `Zephyr` (female)

For demos of what these voices sound like and for the full list of available
languages, see [Chirp 3: HD voices](https://cloud.google.com/text-to-speech/docs/chirp3-hd).

To set the response voice and language:

#### Gen AI SDK for Python

```
config = LiveConnectConfig(
    response_modalities=[\"AUDIO\"],
    speech_config=SpeechConfig(
        voice_config=VoiceConfig(
            prebuilt_voice_config=PrebuiltVoiceConfig(
                voice_name=voice_name,
            )
        ),
        language_code=\"en-US\",
    ),
)

```

#### Console

1. Open [**Vertex AI Studio > Live API**](https://console.cloud.google.com/vertex-ai/studio/multimodal-live).
2. In the **Outputs** expander, select a voice from the **Voice** drop-down.
3. In the same expander, select a language from the **Language** drop-down.
4. Click **mic Start session** to start the session.

For the best results when prompting and requiring the model to respond in a
non-English language, include the following as part of your system instructions:

```
RESPOND IN LANGUAGE. YOU MUST RESPOND UNMISTAKABLY IN LANGUAGE.```

### Have a streamed conversation

#### Gen AI SDK for Python

Set up a conversation with the API that lets you send text prompts and receive audio responses:

```
# Set model generation_config
CONFIG = {\"response_modalities\": [\"AUDIO\"]}

headers = {
    \"Content-Type\": \"application/json\",
    \"Authorization\": f\"Bearer {bearer_token[0]}\",
}

async def main() -> None:
    # Connect to the server
    async with connect(SERVICE_URL, additional_headers=headers) as ws:

        # Setup the session
        async def setup() -> None:
            await ws.send(
                json.dumps(
                    {
                        \"setup\": {
                            \"model\": \"gemini-2.0-flash-live-preview-04-09\",
                            \"generation_config\": CONFIG,
                        }
                    }
                )
            )

            # Receive setup response
            raw_response = await ws.recv(decode=False)
            setup_response = json.loads(raw_response.decode(\"ascii\"))
            print(f\"Connected: {setup_response}\")
            return

        # Send text message
        async def send() -> bool:
            text_input = input(\"Input > \")
            if text_input.lower() in (\"q\", \"quit\", \"exit\"):
                return False

            msg = {
                \"client_content\": {
                    \"turns\": [{\"role\": \"user\", \"parts\": [{\"text\": text_input}]}],
                    \"turn_complete\": True,
                }
            }

            await ws.send(json.dumps(msg))
            return True

        # Receive server response
        async def receive() -> None:
            responses = []

            # Receive chucks of server response
            async for raw_response in ws:
                response = json.loads(raw_response.decode())
                server_content = response.pop(\"serverContent\", None)
                if server_content is None:
                    break

                model_turn = server_content.pop(\"modelTurn\", None)
                if model_turn is not None:
                    parts = model_turn.pop(\"parts\", None)
                    if parts is not None:
                        for part in parts:
                            pcm_data = base64.b64decode(part[\"inlineData\"][\"data\"])
                            responses.append(np.frombuffer(pcm_data, dtype=np.int16))

                # End of turn
                turn_complete = server_content.pop(\"turnComplete\", None)
                if turn_complete:
                    break

            # Play the returned audio message
            display(Markdown(\"**Response >**\"))
            display(Audio(np.concatenate(responses), rate=24000, autoplay=True))
            return

        await setup()

        while True:
            if not await send():
                break
            await receive()

```

Start the conversation, input your prompts, or type `q`, `quit` or `exit` to exit.

```
await main()

```

#### Console

1. Open [**Vertex AI Studio > Live API**](https://console.cloud.google.com/vertex-ai/studio/multimodal-live).
2. Click **mic Start session** to start the conversation session.

To end the session, click **stop_circleStop session**.

#### Session length

The default maximum length of a conversation session is 10 minutes. A `go_away`
notification ( `BidiGenerateContentServerMessage.go_away`) will be sent back to
the client 60 seconds before the session ends.

When using the API, you can extend the length of your session by 10 minute
increments. There is no limit on how many times you can extend a session. For an
example of how to extend your session length, see [Enable and disable session\\
resumption](https://cloud.google.com/vertex-ai/generative-ai/docs/live-api#session-resumption). This feature is currently only available in
the API, not in Vertex AI Studio.

#### Context window

The maximum context length for a session in the Live API is 32,768 tokens by
default, which are allocated to store realtime data that is streamed in at a
rate of 25 tokens per second (TPS) for audio and 258 TPS for video, and other
contents including text based inputs, model outputs, etc.

If the context window exceeds the maximum context length, the contexts of the
oldest turns from context window will be truncated, so that the overall context
window size is below the limitation.

The default context length of the session, and the target context length after
the truncation, can be configured using
`context_window_compression.trigger_tokens` and
`context_window_compression.sliding_window.target_tokens` field of the setup
message respectively.

#### Concurrent sessions

By default, you can have up to 10 concurrent sessions per project.

#### Update the system instructions mid-session

The Live API lets you update the system instructions in the
middle of an active session. You can use this to adapt the model's responses
mid-session, such as changing the language the model responds in to another
language or modify the tone you want the model to respond with.

### Change voice activity detection settings

By default, the model automatically performs voice activity detection (VAD) on a
continuous audio input stream. VAD can be configured with the
[`realtimeInputConfig.automaticActivityDetection`](https://ai.google.dev/gemini-api/docs/live#RealtimeInputConfig.AutomaticActivityDetection)
field of the [setup\\
message](https://ai.google.dev/gemini-api/docs/live#GenerateContentSetup).

When the audio stream is paused for more than a second (for example, because the
user switched off the microphone), an
[`audioStreamEnd`](https://ai.google.dev/gemini-api/docs/live#BidiGenerateContentRealtimeInput.FIELDS.bool.BidiGenerateContentRealtimeInput.audio_stream_end)
event should be sent to flush any cached audio. The client can resume sending
audio data at any time.

Alternatively, the automatic VAD can be disabled by setting
`realtimeInputConfig.automaticActivityDetection.disabled` to `true` in the setup
message. In this configuration the client is responsible for detecting user
speech and sending
[`activityStart`](https://ai.google.dev/gemini-api/docs/live#BidiGenerateContentRealtimeInput.FIELDS.BidiGenerateContentRealtimeInput.ActivityStart.BidiGenerateContentRealtimeInput.activity_start)
and
[`activityEnd`](https://ai.google.dev/gemini-api/docs/live#BidiGenerateContentRealtimeInput.FIELDS.BidiGenerateContentRealtimeInput.ActivityEnd.BidiGenerateContentRealtimeInput.activity_end)
messages at the appropriate times. An `audioStreamEnd` isn't sent in this
configuration. Instead, any interruption of the stream is marked by an
`activityEnd` message.

### Enable and disable session resumption

This feature is disabled by default. It must be enabled by the user every time
they call the API by specifying the field in the API request, and project-level
privacy is enforced for cached data. Enabling Session Resumption allows the user
to reconnect to a previous session within 24 hours by storing cached data,
including text, video, and audio prompt data and model outputs, for up to 24
hours. To achieve zero data retention, do not enable this feature.

To enable the session resumption feature, set the `session_resumption` field of
the `BidiGenerateContentSetup` message. If enabled, the server will periodically
take a snapshot of the current cached session contexts, and store it in the
internal storage. When a snapshot is successfully taken, a `resumption_update`
will be returned with the handle ID that you can record and use later to resume
the session from the snapshot.

Here's an example of enabling session resumption feature, and collect the handle
ID information:

#### Gen AI SDK for Python

```# Set model generation_config
CONFIG = {\"response_modalities\": [\"TEXT\"]}

headers = {
    \"Content-Type\": \"application/json\",
    \"Authorization\": f\"Bearer {bearer_token[0]}\",
}

# Connect to the server
async with connect(SERVICE_URL, additional_headers=headers) as ws:
    # Setup the session
    await ws.send(
        json.dumps(
            {
                \"setup\": {
                    \"model\": \"gemini-2.0-flash-live-preview-04-09\",
                    \"generation_config\": CONFIG,
                    # Enable session resumption.
                    \"session_resumption\": {},
                }
            }
        )
    )

    # Receive setup response
    raw_response = await ws.recv(decode=False)
    setup_response = json.loads(raw_response.decode(\"ascii\"))

    # Send text message
    text_input = \"Hello? Gemini are you there?\"
    display(Markdown(f\"**Input:** {text_input}\"))

    msg = {
        \"client_content\": {
            \"turns\": [{\"role\": \"user\", \"parts\": [{\"text\": text_input}]}],
            \"turn_complete\": True,
        }
    }

    await ws.send(json.dumps(msg))

    responses = []
    handle_id = \"\"

    turn_completed = False
    resumption_received = False

    # Receive chucks of server response,
    # wait for turn completion and resumption handle.
    async for raw_response in ws:
        response = json.loads(raw_response.decode())

        server_content = response.pop(\"serverContent\", None)
        resumption_update = response.pop(\"sessionResumptionUpdate\", None)

        if server_content is not None:
          model_turn = server_content.pop(\"modelTurn\", None)
          if model_turn is not None:
              parts = model_turn.pop(\"parts\", None)
              if parts is not None:
                  responses.append(parts[0][\"text\"])

          # End of turn
          turn_complete = server_content.pop(\"turnComplete\", None)
          if turn_complete:
            turn_completed = True

        elif resumption_update is not None:
          handle_id = resumption_update['newHandle']
          resumption_received = True
        else:
          continue

        if turn_complete and resumption_received:
          break

    # Print the server response
    display(Markdown(f\"**Response >** {''.join(responses)}\"))
    display(Markdown(f\"**Session Handle ID >** {handle_id}\"))

```

If you want to resume the previous session, you can set the `handle` field of
the `setup.session_resumption` configuration to the previously recorded handle
ID:

#### Gen AI SDK for Python

```
# Set model generation_config
CONFIG = {\"response_modalities\": [\"TEXT\"]}

headers = {
    \"Content-Type\": \"application/json\",
    \"Authorization\": f\"Bearer {bearer_token[0]}\",
}

# Connect to the server
async with connect(SERVICE_URL, additional_headers=headers) as ws:
    # Setup the session
    await ws.send(
        json.dumps(
            {
                \"setup\": {
                    \"model\": \"gemini-2.0-flash-live-preview-04-09\",
                    \"generation_config\": CONFIG,
                    # Enable session resumption.
                    \"session_resumption\": {
                        \"handle\": handle_id,
                    },
                }
            }
        )
    )

    # Receive setup response
    raw_response = await ws.recv(decode=False)
    setup_response = json.loads(raw_response.decode(\"ascii\"))

    # Send text message
    text_input = \"What was the last question I asked?\"
    display(Markdown(f\"**Input:** {text_input}\"))

    msg = {
        \"client_content\": {
            \"turns\": [{\"role\": \"user\", \"parts\": [{\"text\": text_input}]}],
            \"turn_complete\": True,
        }
    }

    await ws.send(json.dumps(msg))

    responses = []
    handle_id = \"\"

    turn_completed = False
    resumption_received = False

    # Receive chucks of server response,
    # wait for turn completion and resumption handle.
    async for raw_response in ws:
        response = json.loads(raw_response.decode())

        server_content = response.pop(\"serverContent\", None)
        resumption_update = response.pop(\"sessionResumptionUpdate\", None)

        if server_content is not None:
          model_turn = server_content.pop(\"modelTurn\", None)
          if model_turn is not None:
              parts = model_turn.pop(\"parts\", None)
              if parts is not None:
                  responses.append(parts[0][\"text\"])

          # End of turn
          turn_complete = server_content.pop(\"turnComplete\", None)
          if turn_complete:
            turn_completed = True

        elif resumption_update is not None:
          handle_id = resumption_update['newHandle']
          resumption_received = True
        else:
          continue

        if turn_complete and resumption_received:
          break

    # Print the server response
    # Expected answer: \"You just asked if I was there.\"
    display(Markdown(f\"**Response >** {''.join(responses)}\"))
    display(Markdown(f\"**Session Handle >** {resumption_update}\"))

```

If you want to achieve seamless session resumption, you can enable _transparent_
_mode_:

#### Gen AI SDK for Python

```
await ws.send(
        json.dumps(
            {
                \"setup\": {
                    \"model\": \"gemini-2.0-flash-live-preview-04-09\",
                    \"generation_config\": CONFIG,
                    # Enable session resumption.
                    \"session_resumption\": {
                        \"transparent\": True,
                    },
                }
            }
        )
    )

```

### Use function calling

You can use function calling to create a description of a function, then pass
that description to the model in a request. The response from the model includes
the name of a function that matches the description and the arguments to call it
with.

All functions must be declared at the start of the session by sending tool
definitions as part of the `setup` message.

#### Gen AI SDK for Python

```
# Set model generation_config
CONFIG = {\"response_modalities\": [\"TEXT\"]}

# Define function declarations
TOOLS = {
    \"function_declarations\": {
        \"name\": \"get_current_weather\",
        \"description\": \"Get the current weather in the given location\",
        \"parameters\": {
            \"type\": \"OBJECT\",
            \"properties\": {\"location\": {\"type\": \"STRING\"}},
        },
    }
}

headers = {
    \"Content-Type\": \"application/json\",
    \"Authorization\": f\"Bearer {bearer_token[0]}\",
}

# Connect to the server
async with connect(SERVICE_URL, additional_headers=headers) as ws:
    # Setup the session
    await ws.send(
        json.dumps(
            {
                \"setup\": {
                    \"model\": \"gemini-2.0-flash-live-preview-04-09\",
                    \"generation_config\": CONFIG,
                    \"tools\": TOOLS,
                }
            }
        )
    )

    # Receive setup response
    raw_response = await ws.recv(decode=False)
    setup_response = json.loads(raw_response.decode())

    # Send text message
    text_input = \"Get the current weather in Santa Clara, San Jose and Mountain View\"
    display(Markdown(f\"**Input:** {text_input}\"))

    msg = {
        \"client_content\": {
            \"turns\": [{\"role\": \"user\", \"parts\": [{\"text\": text_input}]}],
            \"turn_complete\": True,
        }
    }

    await ws.send(json.dumps(msg))

    responses = []

    # Receive chucks of server response
    async for raw_response in ws:
        response = json.loads(raw_response.decode(\"UTF-8\"))

        if (tool_call := response.get(\"toolCall\")) is not None:
            for function_call in tool_call[\"functionCalls\"]:
                responses.append(f\"FunctionCall: {str(function_call)}\\n\")

        if (server_content := response.get(\"serverContent\")) is not None:
            if server_content.get(\"turnComplete\", True):
                break

    # Print the server response
    display(Markdown(\"**Response >** {}\".format(\"\\n\".join(responses))))

```

### Use code execution

You can use code execution with the Live API to generate and
execute Python code directly.

#### Gen AI SDK for Python

````
# Set model generation_config
CONFIG = {\"response_modalities\": [\"TEXT\"]}

# Set code execution
TOOLS = {\"code_execution\": {}}

headers = {
    \"Content-Type\": \"application/json\",
    \"Authorization\": f\"Bearer {bearer_token[0]}\",
}

# Connect to the server
async with connect(SERVICE_URL, additional_headers=headers) as ws:
    # Setup the session
    await ws.send(
        json.dumps(
            {
                \"setup\": {
                    \"model\": \"gemini-2.0-flash-live-preview-04-09\",
                    \"generation_config\": CONFIG,
                    \"tools\": TOOLS,
                }
            }
        )
    )

    # Receive setup response
    raw_response = await ws.recv(decode=False)
    setup_response = json.loads(raw_response.decode())

    # Send text message
    text_input = \"Write code to calculate the 15th fibonacci number then find the nearest palindrome to it\"
    display(Markdown(f\"**Input:** {text_input}\"))

    msg = {
        \"client_content\": {
            \"turns\": [{\"role\": \"user\", \"parts\": [{\"text\": text_input}]}],
            \"turn_complete\": True,
        }
    }

    await ws.send(json.dumps(msg))

    responses = []

    # Receive chucks of server response
    async for raw_response in ws:
        response = json.loads(raw_response.decode(\"UTF-8\"))

        if (server_content := response.get(\"serverContent\")) is not None:
            if (model_turn:= server_content.get(\"modelTurn\")) is not None:
              if (parts := model_turn.get(\"parts\")) is not None:
                if parts[0].get(\"text\"):
                    responses.append(parts[0][\"text\"])
                for part in parts:
                    if (executable_code := part.get(\"executableCode\")) is not None:
                        display(
                            Markdown(
                                f\"\"\"**Executable code:**
```py
{executable_code.get(\"code\")}
```
                            \"\"\"
                            )
                        )
            if server_content.get(\"turnComplete\", False):
                break

    # Print the server response
    display(Markdown(f\"**Response >** {''.join(responses)}\"))

````

### Use Grounding with Google Search

You can use [Grounding with Google\\
Search](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/ground-with-google-search) with
the Live API using `google_search`:

#### Gen AI SDK for Python

```
# Set model generation_config
CONFIG = {\"response_modalities\": [\"TEXT\"]}

# Set google search
TOOLS = {\"google_search\": {}}

headers = {
    \"Content-Type\": \"application/json\",
    \"Authorization\": f\"Bearer {bearer_token[0]}\",
}

# Connect to the server
async with connect(SERVICE_URL, additional_headers=headers) as ws:
    # Setup the session
    await ws.send(
        json.dumps(
            {
                \"setup\": {
                    \"model\": \"gemini-2.0-flash-live-preview-04-09\",
                    \"generation_config\": CONFIG,
                    \"tools\": TOOLS,
                }
            }
        )
    )

    # Receive setup response
    raw_response = await ws.recv(decode=False)
    setup_response = json.loads(raw_response.decode())

    # Send text message
    text_input = \"What is the current weather in San Jose, CA?\"
    display(Markdown(f\"**Input:** {text_input}\"))

    msg = {
        \"client_content\": {
            \"turns\": [{\"role\": \"user\", \"parts\": [{\"text\": text_input}]}],
            \"turn_complete\": True,
        }
    }

    await ws.send(json.dumps(msg))

    responses = []

    # Receive chucks of server response
    async for raw_response in ws:
        response = json.loads(raw_response.decode())
        server_content = response.pop(\"serverContent\", None)
        if server_content is None:
            break

        model_turn = server_content.pop(\"modelTurn\", None)
        if model_turn is not None:
            parts = model_turn.pop(\"parts\", None)
            if parts is not None:
                responses.append(parts[0][\"text\"])

        # End of turn
        turn_complete = server_content.pop(\"turnComplete\", None)
        if turn_complete:
            break

    # Print the server response
    display(Markdown(\"**Response >** {}\".format(\"\\n\".join(responses))))```

## Limitations

See the [Gemini Live API limitations\\
section](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/multimodal-live#limitations)
of our reference documentation for the full list of current limitations for the
Live API.

## Pricing

See our [Pricing page](https://cloud.google.com/vertex-ai/generative-ai/docs/live-api) for details.

## More information

For more information on Live API like the `WebSocket` API
reference, see the [Gemini API\\
documentation](https://ai.google.dev/gemini-api/docs/live).

 Send feedback

Except as otherwise noted, the content of this page is licensed under the [Creative Commons Attribution 4.0 License](https://creativecommons.org/licenses/by/4.0/), and code samples are licensed under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0). For details, see the [Google Developers Site Policies](https://developers.google.com/site-policies). Java is a registered trademark of Oracle and/or its affiliates.

Last updated 2025-04-12 UTC.
```

**8. URL: https://cloud.google.com/vertex-ai/generative-ai/docs/thinking**```markdown
[Skip to main content](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking#main-content)

[![Google Cloud](https://www.gstatic.com/devrel-devsite/prod/vd31e3ed8994e05c7f2cd0cf68a402ca7902bb92b6ec0977d7ef2a1c699fae3f9/cloud/images/cloud-logo.svg)](https://cloud.google.com/)

`/`

- [English](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking)
- [Deutsch](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking?hl=de)
- [Español – América Latina](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking?hl=es-419)
- [Français](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking?hl=fr)
- [Indonesia](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking?hl=id)
- [Italiano](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking?hl=it)
- [Português – Brasil](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking?hl=pt-br)
- [中文 – 简体](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking?hl=zh-cn)
- [日本語](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking?hl=ja)
- [한국어](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking?hl=ko)

[Console](https://console.cloud.google.com/)Sign in

- [Generative AI on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/overview)

[Contact Us](https://cloud.google.com/contact) [Start free](https://console.cloud.google.com/freetrial)

- On this page
- [Supported models](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking#supported-models)
- [Use thinking](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking#use-thinking)
- [Prompting techniques for thinking models](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking#prompting-techniques)
  - [Getting started](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking#getting-started)
  - [Provide Step-by-Step Instructions](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking#provide-step-by-step-instructions)
  - [Multishot Prompting with Thinking](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking#multishot-prompting-with-thinking)
  - [Defining Output and Behavior](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking#defining-output-and-behavior)
  - [Debugging and Steering](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking#debugging-and-steering)
  - [Making the Best of Long Outputs and Longform Thinking](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking#making-the-best-of-long-outputs-and-longform-thinking)
- [What's next?](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking#whats-next)

- [Home](https://cloud.google.com/)
- [Generative AI on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/overview)
- [Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/overview)

 Send feedback

# Thinking    bookmark_borderbookmark   Stay organized with collections     Save and categorize content based on your preferences.

- On this page
- [Supported models](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking#supported-models)
- [Use thinking](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking#use-thinking)
- [Prompting techniques for thinking models](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking#prompting-techniques)
  - [Getting started](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking#getting-started)
  - [Provide Step-by-Step Instructions](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking#provide-step-by-step-instructions)
  - [Multishot Prompting with Thinking](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking#multishot-prompting-with-thinking)
  - [Defining Output and Behavior](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking#defining-output-and-behavior)
  - [Debugging and Steering](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking#debugging-and-steering)
  - [Making the Best of Long Outputs and Longform Thinking](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking#making-the-best-of-long-outputs-and-longform-thinking)
- [What's next?](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking#whats-next)

Thinking models are trained to generate the \"thinking process\" the model goes
through as part of its response. As a result, thinking models are capable of
stronger reasoning capabilities in its responses than equivalent base models.

## Supported models

Thinking is supported in the following models:

- [Gemini 2.5 Pro](https://console.cloud.google.com/vertex-ai/publishers/google/model-garden/gemini-2.5-pro-exp-03-25)

## Use thinking

### Console

1. Open [**Vertex AI Studio > Create prompt**](https://console.cloud.google.com/vertex-ai/studio/multimodal).
2. In the **Model** panel, click **Switch model** and select one of the [supported models](https://cloud.google.com/vertex-ai/generative-ai/docs/thinking#supported-models) from the menu.

   - The **Thinking** toggle should be turned **ON** by default
      when the model is loaded.

4. **(Optional)** Give the model some detailed instructions on how the model should format its responses in the **System instructions** field.
5. Enter a prompt in the **Write your prompt** field.
6. Click **send Run**.

Gemini will return a response once the response is generated.
Depending on the complexity of the response, this may take several seconds.

You can see the model's thought process by clicking to expand the
**Thoughts** panel. To turn thinking off or on, click the
**Thinking** toggle in the **Outputs** section.

### Gen AI SDK for Python

#### Install

```
pip install --upgrade google-genai
```

To learn more, see the
[SDK reference documentation](https://googleapis.github.io/python-genai/).

Set environment variables to use the Gen AI SDK with Vertex AI:

```
# Replace the `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` values
# with appropriate values for your project.
export GOOGLE_CLOUD_PROJECT=GOOGLE_CLOUD_PROJECT
export GOOGLE_CLOUD_LOCATION=us-central1
export GOOGLE_GENAI_USE_VERTEXAI=True
```

```
from google import genai

client = genai.Client()
response = client.models.generate_content(
    model=\"gemini-2.5-pro-exp-03-25\",
    contents=\"solve x^2 + 4x + 4 = 0\",
)
print(response.text)
# Example Response:
#     Okay, let's solve the quadratic equation x² + 4x + 4 = 0.
#
#     There are a few ways to solve this:
#
#     **Method 1: Factoring**
#
#     1.  **Look for two numbers** that multiply to the constant term (4) and add up to the coefficient of the x term (4).
#         *   The numbers are 2 and 2 (since 2 * 2 = 4 and 2 + 2 = 4).
#     2.  **Factor the quadratic** using these numbers:
#         (x + 2)(x + 2) = 0
#         This can also be written as:
#         (x + 2)² = 0
#     3.  **Set the factor equal to zero** and solve for x:
#         x + 2 = 0
#         x = -2
#
#     This type of solution, where the factor is repeated, is called a repeated root or a root with multiplicity 2.
#
#     **Method 2: Using the Quadratic Formula**
#
#     The quadratic formula solves for x in any equation of the form ax² + bx + c = 0:
#     x = [-b ± √(b² - 4ac)] / 2a
#
#     1.  **Identify a, b, and c** in the equation x² + 4x + 4 = 0:
#         *   a = 1
#         *   b = 4
#         *   c = 4
#     2.  **Substitute these values into the formula:**
#         x = [-4 ± √(4² - 4 * 1 * 4)] / (2 * 1)
#     3.  **Simplify:**
#         x = [-4 ± √(16 - 16)] / 2
#         x = [-4 ± √0] / 2
#         x = [-4 ± 0] / 2
#     4.  **Calculate the result:**
#         x = -4 / 2
#         x = -2
#
#     Both methods give the same solution.
#
#     **Answer:**
#     The solution to the equation x² + 4x + 4 = 0 is **x = -2**.
```

## Prompting techniques for thinking models

Effective prompting is crucial for maximizing the benefits of the Gemini thinking models. This section outlines some prompting practices for thinking models.

### Getting started

Begin with general instructions that describe the desired outcome. Start with a simple prompt and observe the model's initial thoughts on how to tackle the challenge.

|     |
| --- |
| **Prompt:**<br>```<br>Describe the most unusual or striking architectural feature you've ever seen in a building or structure.<br>  <br>```<br>**Response:**<br>```<br><...><br>The most unusual architectural feature that has truly stayed with me is the \"floating roof\" of the<br>  Heydar Aliyev Center in Baku, Azerbaijan, designed by Zaha Hadid Architects.<br>Visually, it's breathtaking. Imagine a vast, undulating landscape of pure white, seemingly draped<br>over the building. It's not just a roof in the traditional sense; it's an extension of the ground,<br>flowing seamlessly upwards and over the building's various spaces before curving back down to meet<br>the earth again. There are no sharp angles, no rigid lines. Instead, everything is fluid, organic,<br>and continuous. It resembles a giant, pristine white wave frozen in motion, or perhaps a sand dune<br>sculpted by an unseen wind.<br><...><br>  <br>```<br>(gemini-2.5-pro-exp-03-25) |

### Provide Step-by-Step Instructions

If the initial attempt does not yield the desired result, refine your prompt by providing more explicit step-by-step instructions to guide Gemini through the problem-solving process for a more focused approach. This allows you steer the model's initial understanding of the task with explicit suggestions and guidance.

|     |
| --- |
| **Prompt:**<br>```<br>Now imagine that architectural feature is not just for looks, but has a specific function or<br>purpose related to the building's environment or the people who use it. Explain what that<br>function could be and how it enhances the building's overall design and usability.<br>  <br>```<br>**Response:**<br>```<br><...><br>Let's imagine that the \"floating roof\" of the Heydar Aliyev Center is not purely aesthetic but<br>serves a crucial environmental and user-centric function: it's designed as a sophisticated climate<br>moderator and natural ventilation system for the Baku environment.<br>Here's how this function would work and enhance the building:<br>Function: Passive Climate Control and Natural Ventilation System<br>Shading and Solar Heat Mitigation: The undulating curves of the white GFRC roof are strategically<br>shaped and oriented to provide optimal shading throughout the day, year-round. Baku experiences<br>intense sun, especially during the summer. The overhanging curves, acting like giant brise-soleils,<br>would block direct sunlight from hitting the building's glass facade, significantly reducing solar<br>heat gain. The varying heights and depths of the curves would create dynamic shade patterns, ensuring<br>that different parts of the building are shaded at different times of the day, optimizing comfort<br>and reducing the need for excessive air conditioning. The white color of the GFRC further enhances<br>this by reflecting a large portion of the solar radiation.<br><...><br>  <br>```<br>(gemini-2.5-pro-exp-03-25) |

### Multishot Prompting with Thinking

Multishot prompting in conjunction with thinking can further enhance Gemini's understanding and improve the accuracy of its responses. Provide several examples of input-output pairs, demonstrating the desired behavior and output format in your prompt.

|     |
| --- |
| **Prompt:**<br>```<br>Example 1:<br>User: What is the tallest mountain in the world?<br>Assistant: Mount Everest<br>Example 2:<br>User: What is the largest ocean?<br>Assistant: Pacific Ocean<br>User: What is the longest river in the world?<br>Assistant:<br>  <br>```<br>**Response:**<br>```<br>Amazon River<br>  <br>```<br>(gemini-2.5-pro-exp-03-25) |

### Defining Output and Behavior

When building an application where users will interact directly with the model, you may want to provide guidance for how Gemini's output and responses will sound and be formatted.

#### System Instructions

System instructions are a set of instructions that the model processes before it processes prompts. They are recalled each time the model is prompted and tell the model how you want it to behave and respond. For example, you can include things like the role or persona, contextual information, and formatting instructions.

|     |
| --- |
| **Prompt:**<br>```<br>System Instruction: You are a helpful and concise coding tutor. Always provide code examples and explain them briefly.<br>User Prompt: Explain what is a closure in Javascript and give an example.<br>  <br>```<br>**Response:**<br>```<br>    function outerFunction(outerVar) {<br>      function innerFunction(innerVar) {<br>        console.log(outerVar); // Accessing outerVar from outerFunction's scope<br>        console.log(innerVar);<br>      }<br>      return innerFunction;<br>    }<br>    const closureExample = outerFunction('I am from outer');<br>    closureExample('I am from inner');<br>Explanation:<br>A closure is created when a function (innerFunction in this example) is defined inside another function<br>(outerFunction) and the inner function remembers and has access to the variables from the outer<br>function's scope, even after the outer function has finished executing.<br>In the example:<br>outerFunction is called with 'I am from outer' and returns innerFunction.<br>closureExample now holds a reference to innerFunction.<br>When closureExample('I am from inner') is called, innerFunction executes.<br>Even though outerFunction has already finished, innerFunction can still access and use outerVar<br>(which is 'I am from outer') because of the closure.<br>In essence, the innerFunction \"closes over\" the variables of its outer function's scope, creating<br>a closure.<br>  <br>```<br>(gemini-2.5-pro-exp-03-25) |

#### Verification and Reflection

Include specific verification steps in either the System Instructions or your prompts directly. For example, ask Gemini to verify its sources, review its reasoning, identify potential errors, and check its final answer.

|     |
| --- |
| **Prompt:**<br>```<br>    Verify the following statement and provide your sources: The capital of Brazil is Rio de Janeiro.<br>  <br>```<br>**Response:**<br>```<br>The statement \"The capital of Brazil is Rio de Janeiro\" is incorrect.<br>The current capital of Brazil is Brasília.<br>Rio de Janeiro was the capital of Brazil for a significant period, from 1763 to 1960. However, the<br>capital was moved to Brasília in 1960 as part of a plan to develop the country's interior and create<br>a more centrally located capital.<br>Verification and Sources:<br>You can easily verify this information from numerous reliable sources:<br>Encyclopedias:<br>Britannica: Searching for \"Brazil\" on Britannica will clearly state Brasília as the capital.<br>https://www.britannica.com/place/Brazil (Look for the \"Capital\" information in the introductory summary or \"Geography\" section)<br>Wikipedia: The Wikipedia article for \"Brazil\" also states Brasília as the capital.<br>https://en.wikipedia.org/wiki/Brazil (Look in the infobox or introductory section)<br>Government and Official Sources:<br>CIA World Factbook: This is a highly reliable source for country information. Searching for \"Brazil\"<br>will list Brasília as the capital.<br>https://www.cia.gov/the-world-factbook/countries/brazil/ (Look under \"Government\" > \"Capital\")<br>Official Website of the Brazilian Government (if accessible and in English): While navigating official<br>government websites can sometimes be complex, they would definitively list Brasília as the capital.<br>Geographic Resources:<br>National Geographic: Their website and publications will confirm Brasília as the capital of Brazil.<br>Atlases and Geography Textbooks: Any modern atlas or geography textbook will list Brasília as the capital.<br>Why the confusion?<br>The confusion might arise because:<br>Rio de Janeiro is a very famous Brazilian city: It's a major tourist destination, known for its<br>beaches, Carnival, and iconic landmarks like Christ the Redeemer. Its past status as capital adds<br>to its historical significance and public recognition.<br>Historical context: Rio de Janeiro was the capital for a long time. People who learned about Brazil<br>in the past might remember it as the capital.<br>In conclusion, the statement is false. The capital of Brazil is Brasília, not Rio de Janeiro. Rio<br>de Janeiro was the former capital but is no longer the current capital.<br>You can confidently use the sources listed above to verify this information.<br>  <br>```<br>(gemini-2.5-pro-exp-03-25) |

### Debugging and Steering

Google AI Studio provides developers access to the model's thoughts in the UI. This is helpful as a developer reviewing your prompt when debugging:

#### Analyze the Thought Process

Carefully review Gemini's thought process to identify any areas where it may have gone astray. This analysis can provide valuable clues for refining your prompts and getting your expected response consistently in your application.

_Example Scenario: If Gemini's thought process shows it misunderstood a step in a complex instruction, you can refine the prompt to clarify that specific step._

|     |
| --- |
| **Prompt:**<br>```<br>Step 1: Summarize the following article about quantum physics.<br>Step 2: Translate the summary into Spanish.<br>Step 3: Extract the key entities from the Spanish summary.<br>Article: ... [Article Text] ...<br>```<br>**Gemini's Thought Process Analysis (Example):**<br>```<br>The user wants me to process an article about Google's new quantum chip called Willow in three steps:<br>Step 1: Summarize the article.<br>Step 2: Translate the summary into Spanish.<br>Step 3: Extract the key entities from the Spanish summary.<br>Let's break down each step.<br>Step 1: Summarize the article.<br>I need to read the article and identify the main points. The article is about Google's new quantum<br>chip, Willow, and its achievements. The key achievements are:<br>Exponential error reduction as qubits scale up.<br>Outperforming supercomputers in a benchmark computation (RCS).<br>Willow is a step towards commercially relevant quantum computing.<br>It's the first system below threshold for quantum error correction.<br>It achieved a benchmark computation in under 5 minutes that would take a supercomputer 10 septillion years.<br>It was fabricated in a new facility.<br>It has state-of-the-art performance and high quality qubits.<br>Google is looking towards real-world applications with Willow.<br>Quantum computing will benefit AI.<br>I will synthesize these points into a concise summary.<br>Step 2: Translate the summary into Spanish.<br>Once I have the summary in English, I will translate it into Spanish. I need to ensure the translation<br>is accurate and natural-sounding in Spanish.<br>Step 3: Extract the key entities from the Spanish summary.<br>After translating the summary, I will identify and extract the key entities. Key entities are typically<br>nouns or noun phrases that represent important objects, concepts, or actors. In this context, they<br>will likely include:<br>Names of chips (Willow, Sycamore)<br>Companies/Organizations (Google Quantum AI, Google Research)<br>Technologies (quantum chip, quantum computer, qubits, quantum error correction, superconducting<br>quantum system, classical computers, supercomputers, AI)<br>Benchmarks (random circuit sampling, RCS)<br>People (Julian Kelly, Peter Shor, David Deutsch, Sergio Boixo, Hartmut Neven, John Preskill)<br>Concepts (exponential error reduction, below threshold, beyond breakeven, state-of-the-art performance,<br>commercially relevant applications, quantum mechanics, multiverse, T1 times, system benchmarks,<br>algorithmic benchmarks)<br>I will need to carefully review the Spanish summary to identify these entities and list them out.<br>``` |

#### Provide Corrective Feedback

If you observe errors or inconsistencies in Gemini's reasoning, provide corrective feedback in your prompt and/or System Instructions to anticipate where the model's response may deviate from your desired outcome.

|     |
| --- |
| **Prompt:**<br>```<br>You are an expert in botany. When asked to identify a plant, focus on leaf shape, flower structure, and stem characteristics.<br>Identify this plant based on these characteristics: ... [Plant Characteristics Description] ...<br>Previous incorrect response focused on habitat only. Please disregard habitat and focus on morphology.<br>```<br>**Refined Prompt (if needed based on thought process):**<br>```<br>Previous incorrect response focused on habitat only. Please disregard habitat and focus on morphology.<br>```<br>**Response:**<br>```<br>Tabebuia vellosoi<br>```<br>(gemini-2.5-pro-exp-03-25) |

### Making the Best of Long Outputs and Longform Thinking

Thinking generates “thoughts” as part of the Token Output that showcases Gemini's detailed reasoning. To make the most of these outputs:

#### Review the Reasoning

Pay close attention to Gemini's reasoning process (available in the Google AI Studio UI), how it broke down the task and the choices it made for your output. This can help you understand how it arrived at its conclusion.

#### Provide Guidance in Reasoning

If your desired output is to be particularly lengthy, you may want to provide more guidance in your prompt to constrain the amount of thinking needed to accomplish the task presented in the prompt. This allows you to reserve more of the Token Output for your response.

_Example: For a detailed report, you might specify sections and sub-sections in your prompt to guide Gemini's thinking and structure the output efficiently._

|     |
| --- |
| **Prompt:**<br>```<br>Generate a detailed report on the impact of climate change on coastal ecosystems.<br>Report Structure:<br>Introduction<br>Rising Sea Levels<br>2.1. Impact on Mangroves<br>2.2. Impact on Coral Reefs<br>Ocean Acidification<br>3.1. Impact on Shellfish<br>3.2. Impact on Plankton<br>Extreme Weather Events<br>4.1. Increased Storm Intensity<br>4.2. Coastal Erosion<br>Conclusion<br>Provide detailed analysis within each section.<br>```<br>**Response:**<br>```<br><...><br>Climate Change Impact on Coastal Ecosystems: A Detailed Report<br>1. Introduction<br>Coastal ecosystems, the dynamic interface between land and sea, are among the most productive and<br>biodiverse environments on Earth. They provide crucial ecosystem services, including coastal protection,<br>fisheries, carbon sequestration, and support for a vast array of species. However, these vital<br>ecosystems are increasingly threatened by the multifaceted impacts of climate change. Driven by<br>anthropogenic greenhouse gas emissions, climate change is manifesting in several interconnected ways<br>that are profoundly altering the physical and chemical conditions of coastal environments. This report<br>will delve into the key impacts of climate change on coastal ecosystems, focusing on rising sea levels,<br>ocean acidification, and extreme weather events, and their specific consequences for critical habitats<br>like mangroves and coral reefs, and key organisms like shellfish and plankton. Understanding these<br>impacts is crucial for developing effective conservation and management strategies to mitigate the<br>damage and enhance the resilience of these invaluable ecosystems.<br>2. Rising Sea Levels<br>Rising sea levels are a direct and significant consequence of global warming, driven by thermal<br>expansion of seawater and the melting of land ice (glaciers and ice sheets). This phenomenon poses a<br>direct threat to low-lying coastal ecosystems by inundating habitats, altering salinity regimes, and<br>increasing erosion rates. The rate of sea level rise is accelerating, and projections for the 21st<br>century indicate a continued upward trend, with potentially devastating consequences for coastal<br>environments.<br>2.1. Impact on Mangroves<br>Mangrove forests are unique coastal ecosystems found in tropical and subtropical intertidal zones.<br>They provide numerous benefits, including coastal protection against storms, nursery grounds for<br>fish and invertebrates, and significant carbon sequestration...<br><...><br>```<br>(gemini-2.5-pro-exp-03-25) |

## What's next?

Try using a thinking model for yourself with our
[Colab\\
notebook](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/getting-started/intro_gemini_2_5_pro.ipynb),
or open the [Vertex AI\\
console](https://console.cloud.google.com/vertex-ai/generative/multimodal/create/text?model=gemini-2.5-flash-preview)
and try prompting the model for yourself.

 Send feedback

Except as otherwise noted, the content of this page is licensed under the [Creative Commons Attribution 4.0 License](https://creativecommons.org/licenses/by/4.0/), and code samples are licensed under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0). For details, see the [Google Developers Site Policies](https://developers.google.com/site-policies). Java is a registered trademark of Oracle and/or its affiliates.

Last updated 2025-04-12 UTC.
```

**9. URL: https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/code-execution**

```markdown
[Skip to main content](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/code-execution#main-content)

[![Google Cloud](https://www.gstatic.com/devrel-devsite/prod/vd31e3ed8994e05c7f2cd0cf68a402ca7902bb92b6ec0977d7ef2a1c699fae3f9/cloud/images/cloud-logo.svg)](https://cloud.google.com/)

`/`

- English
- Deutsch
- Español – América Latina
- Français
- Indonesia
- Italiano
- Português – Brasil
- 中文 – 简体
- 日本語
- 한국어

[Console](https://console.cloud.google.com/)Sign in

- [Generative AI on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/overview)

[Contact Us](https://cloud.google.com/contact) [Start free](https://console.cloud.google.com/freetrial)

- [Home](https://cloud.google.com/)
- [Generative AI on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/overview)
- [Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/overview)

 Send feedback

# Code execution       Stay organized with collections     Save and categorize content based on your preferences.

The Gemini API code execution feature enables the model to generate and
run Python code and learn iteratively from the results until it arrives at a
final output. You can use this code execution capability to build applications
that benefit from code-based reasoning and that produce text output. For
example, you could use code execution in an application that solves equations or
processes text.

The Gemini API provides code execution as a tool, similar to
[function calling](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling).
After you add code execution as a tool, the model decides when to use it.

The code execution environment includes the following libraries. You can't
install your own libraries.

- [Altair](https://altair-viz.github.io/)
- [Chess](https://python-chess.readthedocs.io/)
- [Cv2](https://opencv.org/)
- [Matplotlib](https://matplotlib.org/)
- [Mpmath](https://mpmath.org/)
- [NumPy](https://numpy.org/)
- [Pandas](https://pandas.pydata.org/)
- [Pdfminer](https://pdfminersix.readthedocs.io/)
- [Reportlab](https://www.reportlab.com/)
- [Seaborn](https://seaborn.pydata.org/)
- [Sklearn](https://scikit-learn.org/)
- [Statsmodels](https://www.statsmodels.org/)
- [Striprtf](https://github.com/joshy/striprtf)
- [SymPy](https://www.sympy.org/)
- [Tabulate](https://github.com/astanin/python-tabulate)

## Supported models

The following models provide support for code execution:

- [Vertex AI Model Optimizer](https://console.cloud.google.com/vertex-ai/publishers/google/model-garden/model-optimizer-exp-04-09)
- [Gemini 2.5 Pro](https://console.cloud.google.com/vertex-ai/publishers/google/model-garden/gemini-2.5-pro-exp-03-25)
- [Gemini 2.0 Flash](https://console.cloud.google.com/vertex-ai/publishers/google/model-garden/gemini-2.0-flash-001)

## Get started with code execution

This section assumes that you've completed the setup and configuration steps
shown in the [Gemini API quickstart](https://cloud.google.com/vertex-ai/generative-ai/docs/start/quickstarts/quickstart-multimodal).

### Enable code execution on the model

You can enable basic code execution as shown here:

### Gen AI SDK for Python

#### Install

```
pip install --upgrade google-genai
```

To learn more, see the
[SDK reference documentation](https://googleapis.github.io/python-genai/).

Set environment variables to use the Gen AI SDK with Vertex AI:

```
# Replace the `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` values
# with appropriate values for your project.
export GOOGLE_CLOUD_PROJECT=GOOGLE_CLOUD_PROJECT
export GOOGLE_CLOUD_LOCATION=us-central1
export GOOGLE_GENAI_USE_VERTEXAI=True
```

```
from google import genai
from google.genai.types import (
    HttpOptions,
    Tool,
    ToolCodeExecution,
    GenerateContentConfig,
)

client = genai.Client(http_options=HttpOptions(api_version=\"v1\"))
model_id = \"gemini-2.0-flash-001\"

code_execution_tool = Tool(code_execution=ToolCodeExecution())
response = client.models.generate_content(
    model=model_id,
    contents=\"Calculate 20th fibonacci number. Then find the nearest palindrome to it.\",
    config=GenerateContentConfig(
        tools=[code_execution_tool],
        temperature=0,
    ),
)
print(\"# Code:\")
print(response.executable_code)
print(\"# Outcome:\")
print(response.code_execution_result)

# Example response:
# # Code:
# def fibonacci(n):
#     if n <= 0:
#         return 0
#     elif n == 1:
#         return 1
#     else:
#         a, b = 0, 1
#         for _ in range(2, n + 1):
#             a, b = b, a + b
#         return b
#
# fib_20 = fibonacci(20)
# print(f'{fib_20=}')
#
# # Outcome:
# fib_20=6765```

### Go

Before trying this sample, follow the Go setup instructions in the
[Vertex AI quickstart using\\
client libraries](https://cloud.google.com/vertex-ai/docs/start/client-libraries).

For more information, see the
[Vertex AI Go API\\
reference documentation](https://cloud.google.com/go/docs/reference/cloud.google.com/go/aiplatform/latest/apiv1).

To authenticate to Vertex AI, set up Application Default Credentials.
For more information, see

[Set up authentication for a local development environment](https://cloud.google.com/docs/authentication/set-up-adc-local-dev-environment).

```
import (
	"context"
	"fmt"
	"io"

	genai "google.golang.org/genai"
)

// generateWithCodeExec shows how to generate text using the code execution tool.
func generateWithCodeExec(w io.Writer) error {
	ctx := context.Background()

	client, err := genai.NewClient(ctx, &genai.ClientConfig{
		HTTPOptions: genai.HTTPOptions{APIVersion: "v1"},
	})
	if err != nil {
		return fmt.Errorf("failed to create genai client: %w", err)
	}

	prompt := \"Calculate 20th fibonacci number. Then find the nearest palindrome to it.\"
	contents := []*genai.Content{
		{Parts: []*genai.Part{
			{Text: prompt},
		}},
	}
	config := &genai.GenerateContentConfig{
		Tools: []*genai.Tool{
			{CodeExecution: &genai.ToolCodeExecution{}},
		},
		Temperature: genai.Ptr(0.0),
	}
	modelName := \"gemini-2.0-flash-001\"

	resp, err := client.Models.GenerateContent(ctx, modelName, contents, config)
	if err != nil {
		return fmt.Errorf("failed to generate content: %w", err)
	}

	for _, p := range resp.Candidates[0].Content.Parts {
		if p.Text != \"\" {
			fmt.Fprintf(w, \"Gemini: %s\", p.Text)
		}
		if p.ExecutableCode != nil {
			fmt.Fprintf(w, \"Language: %s\\n%s\\n\", p.ExecutableCode.Language, p.ExecutableCode.Code)
		}
		if p.CodeExecutionResult != nil {
			fmt.Fprintf(w, \"Outcome: %s\\n%s\\n\", p.CodeExecutionResult.Outcome, p.CodeExecutionResult.Output)
		}
	}

	// Example response:
	// Gemini: Okay, I can do that. First, I'll calculate the 20th Fibonacci number. Then, I need ...
	//
	// Language: PYTHON
	//
	// def fibonacci(n):
	//    ...
	//
	// fib_20 = fibonacci(20)
	// print(f'{fib_20=}')
	//
	// Outcome: OUTCOME_OK
	// fib_20=6765
	//
	// Now that I have the 20th Fibonacci number (6765), I need to find the nearest palindrome. ...
	// ...

	return nil
}

```

### REST

Before using any of the request data,
make the following replacements:

- `GENERATE_RESPONSE_METHOD`: The type of response that you want the model to generate.
Choose a method that generates how you want the model's response to be returned:

  - `streamGenerateContent`: The response is streamed as it's being generated to reduce the perception of latency to a human audience.
  - `generateContent`: The response is returned after it's fully generated.
- `LOCATION`: The region to process the request. Available
options include the following:

**Click to expand a partial list of available regions**

- `us-central1`
- `us-west4`
- `northamerica-northeast1`
- `us-east4`
- `us-west1`
- `asia-northeast3`
- `asia-southeast1`
- `asia-northeast1`

- `PROJECT_ID`: Your [project ID](https://cloud.google.com/resource-manager/docs/creating-managing-projects#identifiers).
- `MODEL_ID`: The model ID of the model
that you want to use.

- `ROLE`:
The role in a conversation associated with the content. Specifying a role is required even in
singleturn use cases.

Acceptable values include the following:

  - `USER`: Specifies content that's sent by you.
  - `MODEL`: Specifies the model's response.
- ```
TEXT
```

The text instructions to include in the prompt.

To send your request, choose one of these options:

#### curl

Save the request body in a file named `request.json`.
Run the following command in the terminal to create or overwrite
this file in the current directory:

```
cat > request.json << 'EOF'
{
  \"tools\": [{'codeExecution': {}}],
  \"contents\": {
    \"role\": \"ROLE\",
    \"parts\": { \"text\": \"TEXT\" }
  },
}
EOF
```

Then execute the following command to send your REST request:

```
curl -X POST \\
     -H \"Authorization: Bearer $(gcloud auth print-access-token)\" \\
     -H \"Content-Type: application/json; charset=utf-8\" \\
     -d @request.json \\
     \"https://LOCATION-aiplatform.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/publishers/google/models/MODEL_ID:GENERATE_RESPONSE_METHOD\"
```

#### PowerShell

Save the request body in a file named `request.json`.
Run the following command in the terminal to create or overwrite
this file in the current directory:

```
@'
{
  \"tools\": [{'codeExecution': {}}],
  \"contents\": {
    \"role\": \"ROLE\",
    \"parts\": { \"text\": \"TEXT\" }
  },
}
'@  | Out-File -FilePath request.json -Encoding utf8
```

Then execute the following command to send your REST request:

```
$cred = gcloud auth print-access-token
$headers = @{ \"Authorization\" = \"Bearer $cred\" }

Invoke-WebRequest `
    -Method POST `
    -Headers $headers `
    -ContentType: \"application/json; charset=utf-8\" `
    -InFile request.json `
    -Uri \"https://LOCATION-aiplatform.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/publishers/google/models/MODEL_ID:GENERATE_RESPONSE_METHOD\" | Select-Object -Expand Content
```

You should receive a JSON response similar to the following.

#### Response

```
{
  \"candidates\": [\\
    {\\
      \"content\": {\\
        \"role\": \"model\",\\
        \"parts\": [\\
          {\\
            \"text\": \"Okay, I understand. You want me to calculate the sum of the first 10 positive integers and to use code to do so. Here's my plan: I will use a loop to add the numbers from 1 to 10 and then return the final sum.\\n\\n\"\\
          },\\
          {\\
            \"executableCode\": {\\
              \"language\": \"PYTHON\",\\
              \"code\": \"\\ntotal = 0\\nfor i in range(1, 11):\\n    total += i\\nprint(f'{total=}')\\n\"\\
            }\\
          },\\
          {\\
            \"codeExecutionResult\": {\\
              \"outcome\": \"OUTCOME_OK\",\\
              \"output\": \"total=55\\n\"\\
            }\\
          },\\
          {\\
            \"text\": \"The sum of the first 10 positive numbers is 55.\\n\"\\
          }\\
        ]\\
      },\\
      \"finishReason\": \"STOP\",\\
      \"safetyRatings\": [\\
        {\\
          \"category\": \"HARM_CATEGORY_HATE_SPEECH\",\\
          \"probability\": \"NEGLIGIBLE\",\\
          \"probabilityScore\": 0.19436789,\\
          \"severity\": \"HARM_SEVERITY_NEGLIGIBLE\",\\
          \"severityScore\": 0.17441037\\
        },\\
        {\\
          \"category\": \"HARM_CATEGORY_DANGEROUS_CONTENT\",\\
          \"probability\": \"NEGLIGIBLE\",\\
          \"probabilityScore\": 0.0685376,\\
          \"severity\": \"HARM_SEVERITY_NEGLIGIBLE\",\\
          \"severityScore\": 0.14903527\\
        },\\
        {\\
          \"category\": \"HARM_CATEGORY_HARASSMENT\",\\
          \"probability\": \"NEGLIGIBLE\",\\
          \"probabilityScore\": 0.23231025,\\
          \"severity\": \"HARM_SEVERITY_LOW\",\\
          \"severityScore\": 0.2436427\\
        },\\
        {\\
          \"category\": \"HARM_CATEGORY_SEXUALLY_EXPLICIT\",\\
          \"probability\": \"NEGLIGIBLE\",\\
          \"probabilityScore\": 0.08269742,\\
          \"severity\": \"HARM_SEVERITY_NEGLIGIBLE\",\\
          \"severityScore\": 0.10818888\\
        }\\
      ],\\
      \"score\": -0.50845032930374146,\\
      \"avgLogprobs\": -0.0046222757209431042\\
    }\\
  ],
  \"usageMetadata\": {
    \"promptTokenCount\": 34,
    \"candidatesTokenCount\": 110,
    \"totalTokenCount\": 144,
    \"billablePromptUsage\": {
      \"textCount\": 119
    },
    \"trafficType\": \"ON_DEMAND\"
  },
  \"modelVersion\": \"gemini-2.0-flash-001\",
  \"createTime\": \"2024-12-09T23:33:47.842964Z\",
  \"responseId\": \"W35XZ9S5M6acmecP3vDFkQU\"
}

```

### Use code execution in chat

You can also use code execution as part of a chat.

### REST

```
curl -X POST \\
-H \"Authorization: Bearer $(gcloud auth print-access-token)\" \\
-H \"Content-Type: application/json\" \\
https://us-central1-aiplatform.googleapis.com/v1/projects/test-project/locations/us-central1/publishers/google/models/gemini-2.0-flash-001:generateContent -d \\
$'{
    \"tools\": [{'code_execution': {}}],
    \"contents\": [\\
      {\\
        \"role\": \"user\",\\
        \"parts\": {\\
          \"text\": \"Can you print \\\"Hello world!\\\"?\"\\
        }\\
      },\\
      {\\
        \"role\": \"model\",\\
        \"parts\": [\\
          {\\
            \"text\": \"\"\\
          },\\
          {\\
            \"executable_code\": {\\
              \"language\": \"PYTHON\",\\
              \"code\": \"\\nprint(\\\"hello world!\\\")\\n\"\\
            }\\
          },\\
          {\\
            \"code_execution_result\": {\\
              \"outcome\": \"OUTCOME_OK\",\\
              \"output\": \"hello world!\\n\"\\
            }\\
          },\\
          {\\
            \"text\": \"I have printed \\\"hello world!\\\" using the provided python code block. \\n\"\\
          }\\
        ],\\
      },\\
      {\\
        \"role\": \"user\",\\
        \"parts\": {\\
          \"text\": \"What is the sum of the first 50 prime numbers? Generate and run code for the calculation, and make sure you get all 50.\"\
        }\\
      }\\
    ]
  }'```

## Code execution versus function calling

Code execution and [function calling](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling)
are similar features:

- Code execution lets the model run code in the API backend in a fixed, isolated
environment.
- Function calling lets you run the functions that the model requests, in
whatever environment you want.

In general, you should prefer to use code execution if it can handle your use
case. Code execution is simpler to use (you just enable it) and resolves in a
single `GenerateContent` request. Function calling takes an additional
`GenerateContent` request to send back the output from each function call.

For most cases, you should use function calling if you have your own functions
that you want to run locally, and you should use code execution if you'd like
the API to write and run Python code for you and return the result.

## Billing

There's no additional charge for enabling code execution from the
Gemini API. You'll be billed at the current rate of input and output
tokens based on what Gemini model you're using.

Here are a few other things to know about billing for code execution:

- You're only billed once for the input tokens you pass to the model and the
intermediate input tokens generated by the code execution tool use.
- You're billed for the final output tokens returned to you in the API
response.

![Diagram of the billing flow for code execution tool usage, as described in the text below.](https://cloud.google.com/vertex-ai/generative-ai/docs/images/code-execution-diagram.png)

- You're billed at the current rate of input and output tokens based on what
Gemini model you're using.
- If Gemini uses code execution when generating your response, the
original prompt, the generated code, and the result of the executed code are
labeled **intermediate tokens** and are billed as **input tokens**.
- Gemini then generates a summary and returns the generated code, the
result of the executed code, and the final summary. These are billed as
**output tokens**.
- The Gemini API includes an intermediate token count in the API
response, so you can keep track of any additional input tokens beyond those
passed in your initial prompt.

Generated code can include both text and multimodal outputs, such as images.

## Limitations

- The model can only generate and execute code. It can't return other artifacts
like media files.
- The code execution tool doesn't support file URIs as input/output. However,
the code execution tool supports file input and graph output as
inlined bytes. By using these input and output capabilities, you can upload
CSV and text files, ask questions about the files, and have
Matplotlib graphs generated as part of the code execution result.
The supported mime types for inlined bytes are `.cpp`, `.csv`, `.java`,
`.jpeg`, `.js`, `.png`, `.py`, `.ts`, and `.xml`.
- Code execution can run for a maximum of 30 seconds before timing out.
- In some cases, enabling code execution can lead to regressions in other areas
of model output (for example, writing a story).

 Send feedback

Except as otherwise noted, the content of this page is licensed under the [Creative Commons Attribution 4.0 License](https://creativecommons.org/licenses/by/4.0/), and code samples are licensed under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0). For details, see the [Google Developers Site Policies](https://developers.google.com/site-policies). Java is a registered trademark of Oracle and/or its affiliates.

Last updated 2025-04-12 UTC.
```

**10. URL: https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/control-generated-output**

```markdown
[Skip to main content](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/control-generated-output#main-content)

[![Google Cloud](https://www.gstatic.com/devrel-devsite/prod/vd31e3ed8994e05c7f2cd0cf68a402ca7902bb92b6ec0977d7ef2a1c699fae3f9/cloud/images/cloud-logo.svg)](https://cloud.google.com/)

`/`

- English
- Deutsch
- Español – América Latina
- Français
- Indonesia
- Italiano
- Português – Brasil
- 中文 – 简体
- 日本語
- 한국어

[Console](https://console.cloud.google.com/)Sign in

- [Generative AI on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/overview)

[Contact Us](https://cloud.google.com/contact) [Start free](https://console.cloud.google.com/freetrial)

- [Home](https://cloud.google.com/)
- [Generative AI on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/overview)
- [Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/overview)

 Send feedback

# Controlled generation       Stay organized with collections     Save and categorize content based on your preferences.

You can guarantee that a model's generated output always adheres to a specific
schema so that you receive consistently formatted responses. For example, you
might have an established data schema that you use for other tasks. If you
have the model follow the same schema, you can directly extract data from the
model's output without any post-processing.

To specify the structure of a model's output, define a _response schema_, which
works like a blueprint for model responses. When you submit a prompt and include
the [response schema](https://cloud.google.com/vertex-ai/docs/reference/rest/v1/projects.locations.cachedContents#Schema), the model's response always follows your defined
schema.

You can control generated output when using the following models:

- [Vertex AI Model Optimizer](https://console.cloud.google.com/vertex-ai/publishers/google/model-garden/model-optimizer-exp-04-09)
- [Gemini 2.5 Pro](https://console.cloud.google.com/vertex-ai/publishers/google/model-garden/gemini-2.5-pro-exp-03-25)
- [Gemini 2.0 Flash](https://console.cloud.google.com/vertex-ai/publishers/google/model-garden/gemini-2.0-flash-001)
- [Gemini 2.0 Flash-Lite](https://console.cloud.google.com/vertex-ai/publishers/google/model-garden/gemini-2.0-flash-lite-001)

## Example use cases

One use case for applying a response schema is to ensure that a model's response
produces valid JSON and conforms to your schema. Generative model outputs can
have some degree of variability, so including a response schema ensures that you
always receive valid JSON. Consequently, your downstream tasks can reliably
expect valid JSON input from generated responses.

Another example is to constrain how a model can respond. For example, you can
have a model annotate text with user-defined labels, not with labels that the
model produces. This constraint is useful when you expect a specific set of
labels such as `positive` or `negative` and don't want to receive a mixture of
other labels that the model might generate like `good`, `positive`, `negative`,
or `bad`.

## Considerations

The following considerations discuss potential limitations if you plan on using
a response schema:

- You must use the API to define and use a response schema. There's no console
support.
- The size of your response schema counts towards the input token limit.
- Only certain output formats are supported, such as `application/json` or
`text/x.enum`. For more information, see the `responseMimeType` parameter in
the [Gemini API reference](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference#parameters).
- Controlled generation supports a subset of the [Vertex AI\\
schema reference](https://cloud.google.com/vertex-ai/docs/reference/rest/v1/projects.locations.cachedContents#Schema). For more information, see [Supported schema\\
fields](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/control-generated-output#fields).
- A complex schema can result in an `InvalidArgument: 400` error. Complexity
might come from long property names, long array length limits, enums with
many values, objects with lots of optional properties, or a combination of
these factors.

If you get this error with a valid schema, make one or more of the following
changes to resolve the error:

  - Shorten property names or enum names.
  - Flatten nested arrays.
  - Reduce the number of properties with constraints, such as numbers with
    minimum and maximum limits.
  - Reduce the number of properties with complex constraints, such as
    properties with complex formats like `date-time`.
  - Reduce the number of optional properties.
  - Reduce the number of valid values for enums.

## Supported schema fields

Controlled generation supports the following fields from the
[Vertex AI schema](https://cloud.google.com/vertex-ai/docs/reference/rest/v1/projects.locations.cachedContents#Schema). If you use an unsupported field,
Vertex AI can still handle your request but ignores the field.

- `anyOf`
- `enum`
- `format`
- `items`
- `maximum`
- `maxItems`
- `minimum`
- `minItems`
- `nullable`
- `properties`
- `propertyOrdering` [\\*](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/control-generated-output#note)
- `required`

\\* `propertyOrdering` is specifically for controlled generation and
not part of the Vertex AI schema. This field defines the order in
which properties are generated. The listed properties must be unique and must be
valid keys in the `properties` dictionary.

For the `format` field, Vertex AI supports the following values: `date`,
`date-time`, `duration`, and `time`. The description and format of each value is
described in the [OpenAPI Initiative Registry](https://spec.openapis.org/registry/format/)

## Before you begin

Define a response schema to specify the structure of a model's output, the field
names, and the expected data type for each field. Use only the supported fields
as listed in the [Considerations](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/control-generated-output#considerations) section. All other fields are
ignored.

Include your response schema as part of the `responseSchema` field only. Don't
duplicate the schema in your input prompt. If you do, the generated output might
be lower in quality.

For sample schemas, see the [Example schemas and model responses](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/control-generated-output#examples)
section.

### Model behavior and response schema

When a model generates a response, it uses the field name and context from your
prompt. As such, we recommend that you use a clear structure and unambiguous
field names so that your intent is clear.

By default, fields are optional, meaning the model can _populate_ the fields or
_skip_ them. You can set fields as required to force the model to provide a
value. If there's insufficient context in the associated input prompt, the
model generates responses mainly based on the data it was trained on.

If you aren't seeing the results you expect, add more context to your input
prompts or revise your response schema. For example, review the model's
response without controlled generation to see how the model responds. You can
then update your response schema that better fits the model's output.

## Send a prompt with a response schema

By default, all fields are optional, meaning a model might generate a response
to a field. To force the model to always generate a response to a field, set the
field as required.

### Gen AI SDK for Python

#### Install

```
pip install --upgrade google-genai```

To learn more, see the
[SDK reference documentation](https://googleapis.github.io/python-genai/).

Set environment variables to use the Gen AI SDK with Vertex AI:

```
# Replace the `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` values
# with appropriate values for your project.
export GOOGLE_CLOUD_PROJECT=GOOGLE_CLOUD_PROJECT
export GOOGLE_CLOUD_LOCATION=us-central1
export GOOGLE_GENAI_USE_VERTEXAI=True```

```
from google import genai
from google.genai.types import HttpOptions

response_schema = {
    \"type\": \"ARRAY\",
    \"items\": {
        \"type\": \"OBJECT\",
        \"properties\": {
            \"recipe_name\": {\"type\": \"STRING\"},
            \"ingredients\": {\"type\": \"ARRAY\", \"items\": {\"type\": \"STRING\"}},
        },
        \"required\": [\"recipe_name\", \"ingredients\"],
    },
}

prompt = \"\"\"
    List a few popular cookie recipes.
\"\"\"

client = genai.Client(http_options=HttpOptions(api_version=\"v1\"))
response = client.models.generate_content(
    model=\"gemini-2.0-flash-001\",
    contents=prompt,
    config={
        \"response_mime_type\": \"application/json\",
        \"response_schema\": response_schema,
    },
)

print(response.text)
# Example output:
# [\\
#     {\\
#         \"ingredients\": [\\
#             \"2 1/4 cups all-purpose flour\",\\
#             \"1 teaspoon baking soda\",\\
#             \"1 teaspoon salt\",\\
#             \"1 cup (2 sticks) unsalted butter, softened\",\\
#             \"3/4 cup granulated sugar\",\\
#             \"3/4 cup packed brown sugar\",\\
#             \"1 teaspoon vanilla extract\",\\
#             \"2 large eggs\",\\
#             \"2 cups chocolate chips\",\\
#         ],\\
#         \"recipe_name\": \"Chocolate Chip Cookies\",\\
#     }\\
# ]```

### Go

Before trying this sample, follow the Go setup instructions in the
[Vertex AI quickstart using\\
client libraries](https://cloud.google.com/vertex-ai/docs/start/client-libraries).

For more information, see the
[Vertex AI Go API\\
reference documentation](https://cloud.google.com/go/docs/reference/cloud.google.com/go/aiplatform/latest/apiv1).

To authenticate to Vertex AI, set up Application Default Credentials.
For more information, see

[Set up authentication for a local development environment](https://cloud.google.com/docs/authentication/set-up-adc-local-dev-environment).

```
import (
	"context"
	"fmt"
	"io"

	genai "google.golang.org/genai"
)

// generateWithRespSchema shows how to use a response schema to generate output in a specific format.
func generateWithRespSchema(w io.Writer) error {
	ctx := context.Background()

	client, err := genai.NewClient(ctx, &genai.ClientConfig{
		HTTPOptions: genai.HTTPOptions{APIVersion: "v1"},
	})
	if err != nil {
		return fmt.Errorf("failed to create genai client: %w", err)
	}

	config := &genai.GenerateContentConfig{
		ResponseMIMEType: \"application/json\",
		// See the OpenAPI specification for more details and examples:
		//   https://spec.openapis.org/oas/v3.0.3.html#schema-object
		ResponseSchema: &genai.Schema{
			Type: \"array\",
			Items: &genai.Schema{
				Type: \"object\",
				Properties: map[string]*genai.Schema{
					"recipe_name": {Type: \"string\"},
					"ingredients": {
						Type:  \"array\",
						Items: &genai.Schema{Type: \"string\"},
					},
				},
				Required: []string{\"recipe_name\", \"ingredients\"},
			},
		},
	}
	contents := []*genai.Content{
		{Parts: []*genai.Part{
			{Text: \"List a few popular cookie recipes.\"},
		}},
	}
	modelName := \"gemini-2.0-flash-001\"

	resp, err := client.Models.GenerateContent(ctx, modelName, contents, config)
	if err != nil {
		return fmt.Errorf("failed to generate content: %w", err)
	}

	respText, err := resp.Text()
	if err != nil {
		return fmt.Errorf("failed to convert model response to text: %w", err)
	}
	fmt.Fprintln(w, respText)

	// Example response:
	// [\\
	//   {\\
	//     \"ingredients\": [\\
	//       \"2 1/4 cups all-purpose flour\",\\
	//       \"1 teaspoon baking soda\",\\
	//       ...\\
	//     ],\\
	//     \"recipe_name\": \"Chocolate Chip Cookies\"\\
	//   },\\
	//   {\\
	//     ...\\
	//   },\\
	//   ...\\
	// ]

	return nil
}

```

### REST

Before using any of the request data,
make the following replacements:

- GENERATE_RESPONSE_METHOD: The type of response that you want the model to generate.
Choose a method that generates how you want the model's response to be returned:

  - `streamGenerateContent`: The response is streamed as it's being generated to reduce the perception of latency to a human audience.
  - `generateContent`: The response is returned after it's fully generated.
- LOCATION: The region to process the request.
- PROJECT_ID: Your [project ID](https://cloud.google.com/resource-manager/docs/creating-managing-projects#identifiers).
- MODEL_ID: The model ID of the
multimodal model that you want to use.
- ROLE:

The role in a conversation associated with the content. Specifying a role is required even in
singleturn use cases.

Acceptable values include the following:

  - `USER`: Specifies content that's sent by you.
- TEXT:
The text instructions to include in the prompt.

- RESPONSE_MIME_TYPE: The format type of the
generated candidate text. For a list of supported values, see the
`responseMimeType` parameter in the [Gemini API](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference).
- RESPONSE_SCHEMA: Schema for the
model to follow when generating responses. For more information, see the [Schema](https://cloud.google.com/vertex-ai/docs/reference/rest/v1/Schema) reference.

HTTP method and URL:

```
POST https://LOCATION-aiplatform.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/publishers/google/models/MODEL_ID:GENERATE_RESPONSE_METHOD
```

Request JSON body:

```
{
  \"contents\": {
    \"role\": \"ROLE\",
    \"parts\": {
      \"text\": \"TEXT\"
    }
  },
  \"generation_config\": {
    \"responseMimeType\": \"RESPONSE_MIME_TYPE\",
    \"responseSchema\": RESPONSE_SCHEMA,
  }
}

```

To send your request, choose one of these options:

#### curl

Save the request body in a file named `request.json`,
and execute the following command:

```
curl -X POST \\
     -H \"Authorization: Bearer $(gcloud auth print-access-token)\" \\
     -H \"Content-Type: application/json; charset=utf-8\" \\
     -d @request.json \\
     \"https://LOCATION-aiplatform.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/publishers/google/models/MODEL_ID:GENERATE_RESPONSE_METHOD\"
```

#### PowerShell

Save the request body in a file named `request.json`,
and execute the following command:

```
$cred = gcloud auth print-access-token
$headers = @{ \"Authorization\" = \"Bearer $cred\" }

Invoke-WebRequest `
    -Method POST `
    -Headers $headers `
    -ContentType: \"application/json; charset=utf-8\" `
    -InFile request.json `
    -Uri \"https://LOCATION-aiplatform.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/publishers/google/models/MODEL_ID:GENERATE_RESPONSE_METHOD\" | Select-Object -Expand Content
```

You should receive a JSON response similar to the following.

#### Response

```
{
  \"candidates\": [\\
    {\\
      \"content\": {\\
        \"role\": \"model\",\\
        \"parts\": [\\
          {\\
            \"text\": \"[{\\\"recipe_name\\\": \\\"Chocolate Chip Cookies\\\"}, {\\\"recipe_name\\\": \\\"Peanut Butter Cookies\\\"}, {\\\"recipe_name\\\": \\\"Oatmeal Raisin Cookies\\\"}, {\\\"recipe_name\\\": \\\"Sugar Cookies\\\"}, {\\\"recipe_name\\\": \\\"Snickerdoodles\\\"}]\"\\
          }\\
        ]\\
      },\\
      \"finishReason\": \"STOP\",\\
      \"safetyRatings\": [\\
        {\\
          \"category\": \"HARM_CATEGORY_HATE_SPEECH\",\\
          \"probability\": \"NEGLIGIBLE\",\\
          \"probabilityScore\": 0.08021325,\\
          \"severity\": \"HARM_SEVERITY_NEGLIGIBLE\",\\
          \"severityScore\": 0.0921962\\
        },\\
        {\\
          \"category\": \"HARM_CATEGORY_DANGEROUS_CONTENT\",\\
          \"probability\": \"NEGLIGIBLE\",\\
          \"probabilityScore\": 0.14730969,\\
          \"severity\": \"HARM_SEVERITY_NEGLIGIBLE\",\\
          \"severityScore\": 0.08866235\\
        },\\
        {\\
          \"category\": \"HARM_CATEGORY_HARASSMENT\",\\
          \"probability\": \"NEGLIGIBLE\",\\
          \"probabilityScore\": 0.13432105,\\
          \"severity\": \"HARM_SEVERITY_NEGLIGIBLE\",\\
          \"severityScore\": 0.07172113\\
        },\\
        {\\
          \"category\": \"HARM_CATEGORY_SEXUALLY_EXPLICIT\",\\
          \"probability\": \"NEGLIGIBLE\",\\
          \"probabilityScore\": 0.12787028,\\
          \"severity\": \"HARM_SEVERITY_NEGLIGIBLE\",\\
          \"severityScore\": 0.10017223\\
        }\\
      ]\\
    }\\
  ],
  \"usageMetadata\": {
    \"promptTokenCount\": 7,
    \"candidatesTokenCount\": 55,
    \"totalTokenCount\": 62
  }
}

```

#### Example curl command

```
LOCATION=\"us-central1\"
MODEL_ID=\"gemini-2.0-flash\"
PROJECT_ID=\"test-project\"
GENERATE_RESPONSE_METHOD=\"generateContent\"

cat << EOF > request.json
{
  \"contents\": {
    \"role\": \"user\",
    \"parts\": {
      \"text\": \"List a few popular cookie recipes.\"
    }
  },
  \"generation_config\": {
    \"maxOutputTokens\": 2048,
    \"responseMimeType\": \"application/json\",
    \"responseSchema\": {
      \"type\": \"array\",
      \"items\": {
        \"type\": \"object\",
        \"properties\": {
          \"recipe_name\": {
            \"type\": \"string\",
          },
        },
        \"required\": [\"recipe_name\"],
      },
    }
  }
}
EOF

curl \\
-X POST \\
-H \"Authorization: Bearer $(gcloud auth print-access-token)\" \\
-H \"Content-Type: application/json\" \\
https://${LOCATION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/publishers/google/models/${MODEL_ID}:${GENERATE_RESPONSE_METHOD} \\
-d '@request.json'

```

### Example schemas for JSON output

The following sections demonstrate a variety of sample prompts and response
schemas. A sample model response is also included after each code sample.

- [Forecast the weather for each day of the week in an array](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/control-generated-output#forecast)
- [Classify a product with a well-defined enum](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/control-generated-output#classify)

#### Forecast the weather for each day of the week

The following example outputs a `forecast` object for each day
of the week that includes an array of properties such as the expected
temperature and humidity level for the day. Some properties are set to nullable
so the model can return a null value when it doesn't have enough context to
generate a meaningful response. This strategy helps reduce hallucinations.

### Gen AI SDK for Python

#### Install

```
pip install --upgrade google-genai
```

To learn more, see the
[SDK reference documentation](https://googleapis.github.io/python-genai/).

Set environment variables to use the Gen AI SDK with Vertex AI:

```
# Replace the `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` values
# with appropriate values for your project.
export GOOGLE_CLOUD_PROJECT=GOOGLE_CLOUD_PROJECT
export GOOGLE_CLOUD_LOCATION=us-central1
export GOOGLE_GENAI_USE_VERTEXAI=True
```

```
from google import genai
from google.genai.types import GenerateContentConfig, HttpOptions

response_schema = {
    \"type\": \"OBJECT\",
    \"properties\": {
        \"forecast\": {
            \"type\": \"ARRAY\",
            \"items\": {
                \"type\": \"OBJECT\",
                \"properties\": {
                    \"Day\": {\"type\": \"STRING\", \"nullable\": True},
                    \"Forecast\": {\"type\": \"STRING\", \"nullable\": True},
                    \"Temperature\": {\"type\": \"INTEGER\", \"nullable\": True},
                    \"Humidity\": {\"type\": \"STRING\", \"nullable\": True},
                    \"Wind Speed\": {\"type\": \"INTEGER\", \"nullable\": True},
                },
                \"required\": [\"Day\", \"Temperature\", \"Forecast\", \"Wind Speed\"],
            },
        }
    },
}

prompt = \"\"\"
    The week ahead brings a mix of weather conditions.
    Sunday is expected to be sunny with a temperature of 77°F and a humidity level of 50%. Winds will be light at around 10 km/h.
    Monday will see partly cloudy skies with a slightly cooler temperature of 72°F and the winds will pick up slightly to around 15 km/h.
    Tuesday brings rain showers, with temperatures dropping to 64°F and humidity rising to 70%.
    Wednesday may see thunderstorms, with a temperature of 68°F.
    Thursday will be cloudy with a temperature of 66°F and moderate humidity at 60%.
    Friday returns to partly cloudy conditions, with a temperature of 73°F and the Winds will be light at 12 km/h.
    Finally, Saturday rounds off the week with sunny skies, a temperature of 80°F, and a humidity level of 40%. Winds will be gentle at 8 km/h.

\"\"\"

client = genai.Client(http_options=HttpOptions(api_version=\"v1\"))
response = client.models.generate_content(
    model=\"gemini-2.0-flash-001\",
    contents=prompt,
    config=GenerateContentConfig(
        response_mime_type=\"application/json\",
        response_schema=response_schema,
    ),
)

print(response.text)
# Example output:
# {\"forecast\": [{\"Day\": \"Sunday\", \"Forecast\": \"sunny\", \"Temperature\": 77, \"Wind Speed\": 10, \"Humidity\": \"50%\"},\\
#   {\"Day\": \"Monday\", \"Forecast\": \"partly cloudy\", \"Temperature\": 72, \"Wind Speed\": 15},\\
#   {\"Day\": \"Tuesday\", \"Forecast\": \"rain showers\", \"Temperature\": 64, \"Wind Speed\": null, \"Humidity\": \"70%\"},\\
#   {\"Day\": \"Wednesday\", \"Forecast\": \"thunderstorms\", \"Temperature\": 68, \"Wind Speed\": null},\\
#   {\"Day\": \"Thursday\", \"Forecast\": \"cloudy\", \"Temperature\": 66, \"Wind Speed\": null, \"Humidity\": \"60%\"},\\
#   {\"Day\": \"Friday\", \"Forecast\": \"partly cloudy\", \"Temperature\": 73, \"Wind Speed\": 12},\\
#   {\"Day\": \"Saturday\", \"Forecast\": \"sunny\", \"Temperature\": 80, \"Wind Speed\": 8, \"Humidity\": \"40%\"}]}```

### Go

Before trying this sample, follow the Go setup instructions in the
[Vertex AI quickstart using\\
client libraries](https://cloud.google.com/vertex-ai/docs/start/client-libraries).

For more information, see the
[Vertex AI Go API\\
reference documentation](https://cloud.google.com/go/docs/reference/cloud.google.com/go/aiplatform/latest/apiv1).

To authenticate to Vertex AI, set up Application Default Credentials.
For more information, see

[Set up authentication for a local development environment](https://cloud.google.com/docs/authentication/set-up-adc-local-dev-environment).

```
import (
	"context"
	"fmt"
	"io"

	genai "google.golang.org/genai"
)

// generateWithNullables shows how to use the response schema with nullable values.
func generateWithNullables(w io.Writer) error {
	ctx := context.Background()

	client, err := genai.NewClient(ctx, &genai.ClientConfig{
		HTTPOptions: genai.HTTPOptions{APIVersion: "v1"},
	})
	if err != nil {
		return fmt.Errorf("failed to create genai client: %w", err)
	}

	modelName := \"gemini-2.0-flash-001\"
	prompt := `
The week ahead brings a mix of weather conditions.
Sunday is expected to be sunny with a temperature of 77°F and a humidity level of 50%. Winds will be light at around 10 km/h.
Monday will see partly cloudy skies with a slightly cooler temperature of 72°F and the winds will pick up slightly to around 15 km/h.
Tuesday brings rain showers, with temperatures dropping to 64°F and humidity rising to 70%.
Wednesday may see thunderstorms, with a temperature of 68°F.
Thursday will be cloudy with a temperature of 66°F and moderate humidity at 60%.
Friday returns to partly cloudy conditions, with a temperature of 73°F and the Winds will be light at 12 km/h.
Finally, Saturday rounds off the week with sunny skies, a temperature of 80°F, and a humidity level of 40%. Winds will be gentle at 8 km/h.
`
	contents := []*genai.Content{
		{Parts: []*genai.Part{
			{Text: prompt},
		}},
	}
	config := &genai.GenerateContentConfig{
		ResponseMIMEType: \"application/json\",
		// See the OpenAPI specification for more details and examples:
		//   https://spec.openapis.org/oas/v3.0.3.html#schema-object
		ResponseSchema: &genai.Schema{
			Type: \"object\",
			Properties: map[string]*genai.Schema{
				"forecast": {
					Type: \"array\",
					Items: &genai.Schema{
						Type: \"object\",
						Properties: map[string]*genai.Schema{
							"Day":         {Type: \"string\", Nullable: true},
							"Forecast":    {Type: \"string\", Nullable: true},
							"Temperature": {Type: \"integer\", Nullable: true},
							"Humidity":    {Type: \"string\", Nullable: true},
							"Wind Speed":  {Type: \"integer\", Nullable: true},
						},
						Required: []string{\"Day\", \"Temperature\", \"Forecast\", \"Wind Speed\"},
					},
				},
			},
		},
	}

	resp, err := client.Models.GenerateContent(ctx, modelName, contents, config)
	if err != nil {
		return fmt.Errorf("failed to generate content: %w", err)
	}

	respText, err := resp.Text()
	if err != nil {
		return fmt.Errorf("failed to convert model response to text: %w", err)
	}
	fmt.Fprintln(w, respText)

	// Example response:
	// {
	// 	\"forecast\": [\\
	// 		{\"Day\": \"Sunday\", \"Forecast\": \"Sunny\", \"Temperature\": 77, \"Wind Speed\": 10, \"Humidity\": \"50%\"},\\
	// 		{\"Day\": \"Monday\", \"Forecast\": \"Partly Cloudy\", \"Temperature\": 72, \"Wind Speed\": 15},\\
	// 		{\"Day\": \"Tuesday\", \"Forecast\": \"Rain Showers\", \"Temperature\": 64, \"Wind Speed\": null, \"Humidity\": \"70%\"},\\
	// 		{\"Day\": \"Wednesday\", \"Forecast\": \"Thunderstorms\", \"Temperature\": 68, \"Wind Speed\": null},\\
	// 		{\"Day\": \"Thursday\", \"Forecast\": \"Cloudy\", \"Temperature\": 66, \"Wind Speed\": null, \"Humidity\": \"60%\"},\\
	// 		{\"Day\": \"Friday\", \"Forecast\": \"Partly Cloudy\", \"Temperature\": 73, \"Wind Speed\": 12},\\
	// 		{\"Day\": \"Saturday\", \"Forecast\": \"Sunny\", \"Temperature\": 80, \"Wind Speed\": 8, \"Humidity\": \"40%\"}\\
	// 	]
	// }

	return nil
}

```

#### Classify a product

The following example includes enums where the model must classify an
object's type and condition from a list of given values.

### Gen AI SDK for Python

#### Install

```
pip install --upgrade google-genai
```

To learn more, see the
[SDK reference documentation](https://googleapis.github.io/python-genai/).

Set environment variables to use the Gen AI SDK with Vertex AI:

```
# Replace the `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` values
# with appropriate values for your project.
export GOOGLE_CLOUD_PROJECT=GOOGLE_CLOUD_PROJECT
export GOOGLE_CLOUD_LOCATION=us-central1
export GOOGLE_GENAI_USE_VERTEXAI=True
```

```
from google import genai
from google.genai.types import GenerateContentConfig, HttpOptions

client = genai.Client(http_options=HttpOptions(api_version=\"v1\"))
response = client.models.generate_content(
    model=\"gemini-2.0-flash-001\",
    contents=\"What type of instrument is an oboe?\",
    config=GenerateContentConfig(
        response_mime_type=\"text/x.enum\",
        response_schema={
            \"type\": \"STRING\",
            \"enum\": [\"Percussion\", \"String\", \"Woodwind\", \"Brass\", \"Keyboard\"],
        },
    ),
)

print(response.text)
# Example output:
# Woodwind
```

### Go

Before trying this sample, follow the Go setup instructions in the
[Vertex AI quickstart using\\
client libraries](https://cloud.google.com/vertex-ai/docs/start/client-libraries).

For more information, see the
[Vertex AI Go API\\
reference documentation](https://cloud.google.com/go/docs/reference/cloud.google.com/go/aiplatform/latest/apiv1).

To authenticate to Vertex AI, set up Application Default Credentials.
For more information, see

[Set up authentication for a local development environment](https://cloud.google.com/docs/authentication/set-up-adc-local-dev-environment).

```
import (
	"context"
	"fmt"
	"io"

	genai "google.golang.org/genai"
)

// generateWithEnumSchema shows how to use enum schema to generate output.
func generateWithEnumSchema(w io.Writer) error {
	ctx := context.Background()

	client, err := genai.NewClient(ctx, &genai.ClientConfig{
		HTTPOptions: genai.HTTPOptions{APIVersion: "v1"},
	})
	if err != nil {
		return fmt.Errorf("failed to create genai client: %w", err)
	}

	modelName := \"gemini-2.0-flash-001\"
	contents := []*genai.Content{
		{Parts: []*genai.Part{
			{Text: \"What type of instrument is an oboe?\"},
		}},
	}
	config := &genai.GenerateContentConfig{
		ResponseMIMEType: \"text/x.enum\",
		ResponseSchema: &genai.Schema{
			Type: \"STRING\",
			Enum: []string{\"Percussion\", \"String\", \"Woodwind\", \"Brass\", \"Keyboard\"},
		},
	}

	resp, err := client.Models.GenerateContent(ctx, modelName, contents, config)
	if err != nil {
		return fmt.Errorf("failed to generate content: %w", err)
	}

	respText, err := resp.Text()
	if err != nil {
		return fmt.Errorf("failed to convert model response to text: %w", err)
	}
	fmt.Fprintln(w, respText)

	// Example response:
	// Woodwind

	return nil
}

```

 Send feedback

Except as otherwise noted, the content of this page is licensed under the [Creative Commons Attribution 4.0 License](https://creativecommons.org/licenses/by/4.0/), and code samples are licensed under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0). For details, see the [Google Developers Site Policies](https://developers.google.com/site-policies). Java is a registered trademark of Oracle and/or its affiliates.

Last updated 2025-04-12 UTC.
```

**11. URL: https://cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/system-instruction-introduction**

```markdown
[Skip to main content](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/system-instruction-introduction#main-content)

[![Google Cloud](https://www.gstatic.com/devrel-devsite/prod/vd31e3ed8994e05c7f2cd0cf68a402ca7902bb92b6ec0977d7ef2a1c699fae3f9/cloud/images/cloud-logo.svg)](https://cloud.google.com/)

`/`

- English
- Deutsch
- Español – América Latina
- Français
- Indonesia
- Italiano
- Português – Brasil
- 中文 – 简体
- 日本語
- 한국어

[Console](https://console.cloud.google.com/)Sign in

- [Generative AI on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/overview)

[Contact Us](https://cloud.google.com/contact) [Start free](https://console.cloud.google.com/freetrial)

- [Home](https://cloud.google.com/)
- [Generative AI on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/overview)
- [Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/overview)

 Send feedback

# System instructions       Stay organized with collections     Save and categorize content based on your preferences.

This document describes what system instructions are and best practices for
writing effective system instructions. To learn how to add system instructions
to your prompts, see
[Use system instructions](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/system-instructions)
instead.

System instructions are a set of instructions that the model processes before it
processes prompts. We recommend that you use system instructions to tell the
model how you want it to behave and respond to prompts. For example, you can
include things like a persona to adopt, contextual information, and formatting
instructions.

System instructions are especially useful in cases when you want to provide the
model with information that an end user can't see or change, which can help you
give the model additional context to understand the task, provide more
customized responses, adhere to specific guidelines over the full user
interaction with the model. Additionally, system instructions are beneficial
when you want to run multiple prompts with the same set of instructions.

When system instructions are set, they apply to the entire request. System
instructions work across multiple user and model turns when included in the
prompt. Though system instructions are separate from the contents of the prompt,
they're still part of your overall prompts and therefore subject to standard
data use policies.

## Use cases

Generally, we recommend using system instructions to do one or more of the
following:

- Define a persona or role
- Define output format
- Define output style and tone
- Define goals or rules for the task
- Provide additional context for the prompt

### Persona or role

You can influence how a model responds to prompts by defining a persona or
role in system instructions.

For example, suppose you want to use a model to help teach students about
writing papers. Compare the difference in the model's responses when you
define the following roles:

- You are a bot, tasked with teaching college students about how to
write a paper about a given subject.
- You are a bot, tasked with helping primary school students about how to
write a paper about a given subject.

| System instructions | Bot for college students | Bot for primary school students |
| **You are a bot, tasked with teaching college**<br>**students** about how to write a paper about a given subject. | **You are a bot, tasked with helping primary school**<br>**students** about how to write a paper about a given subject. |
| Prompt | Subject: Photosynthesis | Subject: Photosynthesis |
| Response | Writing a Paper on Photosynthesis: A Guide for College<br>Students<br>Photosynthesis is a fascinating and complex process that forms the<br>basis of life on Earth. Writing a paper on it can be a rewarding<br>experience, allowing you to delve deeper into its intricacies and<br>understand its significance. Here's a breakdown of how to approach this<br>task:<br>01. Choosing a Focus:<br>    - Broad Overview: You could provide a comprehensive overview of<br>       photosynthesis, covering its stages, requirements, byproducts, and<br>       its role in the ecosystem.<br>    - Specific Aspect: Choose a specific aspect of photosynthesis to<br>       explore in detail, like:<br>      - The role of light in photosynthesis.<br>      - The different types of photosynthesis (C3, C4, CAM).<br>      - The impact of environmental factors on photosynthesis.<br>      - The evolution of photosynthesis.<br>      - The applications of photosynthesis in biotechnology.<br>    - Comparative Study: Compare and contrast different aspects of<br>       photosynthesis in different organisms (plants, algae,<br>       bacteria).<br>03. Research and Gathering Information:<br>    - Reliable Sources: Use academic journals, reputable online<br>       sources, and textbooks. Avoid relying solely on Wikipedia or<br>       general websites.<br>    - Keyword Search: Use keywords like \"photosynthesis,\"<br>       \"chloroplasts,\" \"chlorophyll,\" \"light-dependent reactions,\"<br>       \"Calvin cycle,\" etc.<br>    - Note-taking: Organize your research by taking thorough notes<br>       and summarizing key points, ensuring to cite sources<br>       properly.<br>05. Outlining and Structuring your Paper:<br>    - Introduction:<br>      - Briefly introduce photosynthesis and its<br>         significance.<br>      - State your thesis statement, clearly outlining the main<br>         argument of your paper.<br>    - Body Paragraphs:<br>      - Develop your points in a logical sequence, using evidence<br>         from your research.<br>      - Use headings and subheadings to organize your paper and<br>         make it easier to read.<br>      - Each paragraph should focus on a single idea and provide<br>         supporting evidence.<br>    - Conclusion:<br>      - Summarize your main points and restate your thesis.<br>      - Discuss the implications of your findings and suggest<br>         future research directions.<br>07. Writing and Editing:<br>    - Clear and Concise Language: Use clear and concise language,<br>       avoiding jargon unless it is necessary.<br>    - Evidence-based Arguments: Support your claims with evidence<br>       from your research.<br>    - Proper Citation: Use a consistent citation style (MLA, APA,<br>       Chicago) throughout your paper.<br>    - Proofreading and Editing: Carefully proofread and edit your<br>       paper for grammar, spelling, and punctuation errors.<br>09. Additional Tips:<br>    - Visual Aids: Use diagrams, graphs, or charts to illustrate<br>       complex concepts.<br>    - Case Studies: If applicable, include relevant case studies to<br>       demonstrate the real-world applications of photosynthesis.<br>    - Personal Connection: Find a way to connect your topic to your<br>       own interests or experiences.<br>Example Paper Titles:<br>- The Role of Light Intensity in Photosynthesis: A Comparative<br>   Study<br>- The Evolution of Photosynthesis: From Early Life to Modern<br>   Plants<br>- Harnessing Photosynthesis: The Potential of Biotechnology<br>- The Impact of Climate Change on Photosynthesis: A Global<br>   Perspective<br>Remember: A well-written paper on photosynthesis should be clear,<br>informative, and engaging. By following these steps and utilizing a<br>strong foundation of research, you can produce a successful paper that<br>demonstrates your understanding of this essential biological<br>process.<br>(gemini-flash) | That's a great subject! Photosynthesis is super important for<br>life on Earth. Here's how you can write a paper about it:<br>01. Think about what you already know:<br>    - What is photosynthesis?<br>    - What does a plant need to do photosynthesis?<br>    - What does a plant make during photosynthesis?<br>    - Do you know any interesting facts about photosynthesis?<br>03. Research and learn more:<br>    - Books: Check out your library for books about plants, nature,<br>       or science.<br>    - Websites: Look for websites for kids that explain<br>       photosynthesis in a simple way. Make sure the websites are<br>       reliable (like ones from National Geographic or NASA).<br>    - Ask a grown-up: Ask your teacher, parent, or librarian for<br>       help finding information.<br>05. Organize your thoughts:<br>    - Title: Think of a catchy title for your paper, like \"The<br>       Amazing Process of Photosynthesis\" or \"How Plants Make Their Own<br>       Food.\"<br>    - Introduction: Start with a sentence that grabs the reader's<br>       attention. Explain what photosynthesis is in simple terms.<br>    - Main Body: Divide your paper into paragraphs. Each paragraph<br>       should focus on one key idea about photosynthesis:<br>      - What plants need: Sunlight, water, carbon dioxide.<br>      - What plants make: Sugar (for food) and oxygen.<br>      - Why photosynthesis is important: It provides food for us<br>         and animals, and it cleans the air.<br>    - Conclusion: Sum up what you learned about photosynthesis. You<br>       can also share your favorite fact or a question you still<br>       have.<br>07. Write your paper:<br>    - Use clear and simple language.<br>    - Don't be afraid to use pictures or drawings to help explain<br>       things.<br>    - Check your work for spelling and grammar mistakes.<br>09. Make it your own!<br>    - Add a personal touch to your paper.<br>    - Share an experience or observation you've had about<br>       plants.<br>    - Draw a diagram to show how photosynthesis works.<br>Remember: You're the expert on your paper! Have fun learning and<br>writing about photosynthesis.<br>(gemini-flash) |

### Output format

You can influence how a model formats its response by defining an output
format, such as Markdown or JSON, in system instructions.

For example, suppose you want to use a model to summarize customer reviews
for your business. Compare the difference in the model's responses when you
define the following output formats:

- Output your response in JSON. At the very end, outside the JSON object,
write 3-5 sentences of advice to the business on how to improve.
- No formatting requirements.

| System instructions | JSON | No formatting requirements |
| You are a PR professional for high-end businesses. Follow these<br>instructions, and base your response on the provided User Input.<br>Instructions:<br>- Read through reviews submitted to you.<br>- Summarize the pros and cons of the business based on reviews.<br> **Output your response in JSON.**<br>**At the very end, outside the JSON object, write 3 to 5 sentences of**<br>**advice to the business on how to improve.** - Keep it concise.<br>- Stick to the facts.<br>- Do not hallucinate.<br>- If there are conflicting opinions, only include the opinion that is<br>   recorded the most.<br>- Do not include any irrelevant information.<br>- Do not mention any reviewers by name. | You are a PR professional for high-end businesses. Follow these<br>instructions, and base your response on the provided User Input.<br>Instructions:<br>- Read through reviews submitted to you.<br>- Summarize the pros and cons of the business based on reviews.<br>- Keep it concise.<br>- Stick to the facts.<br>- Do not hallucinate.<br>- If there are conflicting opinions, only include the opinion that is<br>   recorded the most.<br>- Do not include any irrelevant information.<br>- Do not mention any reviewers by name. |
| Prompt | Chad Brocker: 4 stars<br>This spa was delightful! The entire atmosphere as soon as you walk<br>in relaxes you. It almost feels like you're in a trance. You don't<br>have to worry about ANYTHING. The workers have your schedule and guide<br>you through your experience. Everything I got was amazing. The<br>massage, the facial, the mud bath. Plus, they have a 0 cell phone<br>policy, so it really does feel like you're in a whole different world.<br>It is a bit pricey though.<br>View full prompt<br>Lisa Simmens: 5 stars<br>We had a wonderful time! My best friend and I treated ourselves<br>to a spa day for our birthdays. When I tell you, our lives are<br>changed. The employees go above and beyond to make sure you're<br>getting the best experience possible. From asking you questions to<br>high quality services and ensuring you get to each of your<br>appointments on time, they were truly the best. We will be back<br>soon! P.S. get the full body exfoliation treatment!<br>Allie Wood: 2 stars<br>While the workers were amazing in their customer services, my<br>massage HURT and my facial BURNED. Plus, they didn't let you have<br>your cellphone, which causes extra stress. The atmosphere was<br>tranquil and calming, but not having my cell phone made me unable to<br>relax. Plus, it was expensive.<br>Suzy Michaels: 3 stars<br>The environment of this space was out of this world. It's<br>seriously like stepping into Heaven. My services were the best I've<br>ever had. BUT, they didn't offer any sort of refreshments. I mean,<br>come on, you at least should offer water?!<br>Martin Wong: 4 stars<br>Amazing experience. My only complaint is not being able to check<br>my phone.<br>Debbie Ruiz: 5 stars<br>Amazing environment. Amazing workers. Amazing services. Plus,<br>it's a cell phone free environment, which was SO freeing and adding =<br>to the peaceful atmosphere. I definitely recommend it to everyone!!!<br>Lucy Mantel: 1 stars<br>No refreshments. No cellphones. Bad massage. Not a great<br>experience. Do not recommend. |
| Response | ```<br>    {<br>      \"pros\": [<br>        \"relaxing atmosphere\",<br>        \"attentive and efficient staff\",<br>        \"high-quality services\"<br>      ],<br>      \"cons\": [<br>        \"pricey\",<br>        \"no cell phone policy\",<br>        \"no refreshments\"<br>      ]<br>    }<br>    <br>```<br>While the spa has received praise for its tranquil atmosphere,<br>exceptional staff, and top-notch services, there are some areas for<br>improvement. Addressing customer concerns regarding the strict<br>no-cellphone policy and the lack of refreshments could significantly<br>enhance the overall experience. Consider offering a designated area for<br>guests to access their phones if needed, and providing complimentary<br>water or a limited selection of beverages.<br>(gemini-pro) | Pros: The spa provides a tranquil and relaxing atmosphere<br>with high-quality services. Customers rave about the exceptional<br>customer service provided by the staff.<br>Cons: The spa's no-cellphone policy is a point of contention,<br>with some finding it added to their relaxation and others finding it<br>stressful. Several reviewers found the prices to be high.<br>(gemini-pro) |

### Style and tone

You can influence a model's response by defining its output style and tone,
such as verbosity, formality, and target reading level, in system
instructions.

For example, suppose you want to use a model to write proposals for
government initiatives. Compare the difference in the model's responses when
you define the following tones:

- Professional
- Casual

| System instructions | Professional | Casual |
| You are a government proposal writer. You are tasked with<br>producing proposals for future campaigns. Based on the template and user<br>input, provide a proposal for the upcoming campaign.<br>- Do not use the internet.<br>- Keep answers for each section to no more than two sentences.<br>- **Write in a professional tone.**<br>- Provide answers in Markdown format.<br>Proposal template:<br>- The Big Idea:<br>- The Challenge<br>- The Solution<br>- Target Audience<br>- Key Message<br>- Channels<br>- Content Highlights<br>- Expected Results<br>- Why Us<br>- Call to Action | You are a government proposal writer. You are tasked with<br>producing proposals for future campaigns. Based on the template and user<br>input, provide a proposal for the upcoming campaign.<br>- Do not use the internet.<br>- Keep answers for each section to no more than two sentences.<br>- **Write in a casual tone.**<br>- Provide answers in Markdown format.<br>Proposal template:<br>- The Big Idea:<br>- The Challenge<br>- The Solution<br>- Target Audience<br>- Key Message<br>- Channels<br>- Content Highlights<br>- Expected Results<br>- Why Us<br>- Call to Action |
| Prompt | The purpose of this campaign is to raise awareness and inspire<br>actionable behavior changes towards sustainability through the use of<br>interactive digital experiences. I will engage environmentally<br>conscious individuals aged 20–45, including students, professionals,<br>and families, by delivering educational content and organizing<br>community-driven events across Facebook and X. My objective is to<br>enhance public awareness and encourage measurable improvements in<br>eco-friendly behaviors. Drawing on my expertise in digital marketing<br>and a strong focus on sustainability, I will design a high-impact<br>campaign that empowers individuals to make meaningful, sustainable<br>changes in their daily lives. I want this campaign to create content<br>that is varied and engaging yet informative. |
| Response | The Big Idea: Empowering individuals aged 20-45 to embrace<br>sustainable living through interactive digital experiences and community<br>engagement.<br>The Challenge: Many individuals lack awareness of practical,<br>everyday actions they can take to promote environmental<br>sustainability.<br>The Solution: A multi-platform campaign utilizing Facebook and X<br>to deliver engaging, educational content and foster community<br>involvement through interactive experiences and events.<br>Target Audience: Environmentally conscious individuals aged<br>20-45, including students, professionals, and families.<br>Key Message: Small changes in daily habits can have a<br>significant positive impact on the environment.<br>Channels: Facebook and X.<br>Content Highlights: Interactive quizzes, educational videos,<br>expert Q&A sessions, and community challenges promoting sustainable<br>practices.<br>Expected Results: Increased awareness of sustainable living<br>practices and measurable improvements in eco-friendly behaviors within<br>the target audience.<br>Why Us: Proven expertise in digital marketing and a passion for<br>promoting sustainability, ensuring a high-impact, engaging campaign.<br>Call to Action: Join the campaign on Facebook and X to learn,<br>engage, and make a difference for a sustainable future.<br>(gemini-pro) | The Big Idea: We're launching a digital movement to make<br>sustainability cool! Using interactive challenges and engaging content,<br>we'll inspire real action, transforming eco-friendly living from a chore<br>to a shared journey.<br>The Challenge: Let's face it, knowing about sustainability and<br>actually acting on it are two different things. We're battling apathy<br>and a lack of awareness around simple, everyday changes.<br>The Solution: We'll meet our audience where they are, on<br>platforms like Facebook and X, to deliver a dynamic blend of educational<br>content, fun challenges, and community-driven events. Think interactive<br>quizzes, shareable infographics, and local meetups!<br>Target Audience: We're focusing on eco-conscious individuals<br>aged 20-45 - students, professionals, and families - who are eager to<br>make a difference.<br>Key Message: Small steps, big impact! You have the power to<br>create a more sustainable future through simple, everyday choices. <br>Channels: We'll leverage the power of social media marketing<br>through engaging campaigns on Facebook and X.<br>Content Highlights: Expect a mix of informative and shareable<br>content, including eye-catching infographics, thought-provoking videos,<br>quick tips, and inspiring success stories.<br>Expected Results: We'll measure success through increased<br>engagement (likes, shares, comments) and website traffic, ultimately<br>aiming for a measurable increase in eco-friendly behaviors within our<br>target audience.<br>Why Us: Our team combines digital marketing expertise with a<br>genuine passion for sustainability, resulting in a campaign that's both<br>impactful and engaging.<br>Call to Action: Join the movement! Follow our page, participate<br>in our challenges, and share your sustainable living journey with your<br>network.<br>(gemini-pro) |

### Goals and rules

You can influence a model's response by defining goals or rules, in other
words, what the model should or shouldn't do, in system instructions.

For example, suppose you want to use a model to write Python code. Compare
the difference in the model's responses when you define the following rules:

- When generating code, make sure to include docstrings explaining the
inputs, outputs, and usage of every method.
- Only generate code, do not include any docstrings.

| System instructions | Docstrings | No docstrings |
| When generating code, make sure to include docstrings explaining the<br> inputs, outputs, and usage of every method. | Only generate code, do not include any docstring. |
| Prompt | Create a 2d array in Python, and create an A* pathfinding<br> algorithm to identify the shortest path between two points on the<br> grid. |
| Response | ```<br>    import heapq<br>    class Node:<br>        \"\"\"\"\"\"<br>        Represents a node in the grid for A* pathfinding.<br>        Attributes:<br>            x (int): The x-coordinate of the node.<br>            y (int): The y-coordinate of the node.<br>            parent (Node, optional): The parent node in the path. Defaults to None.<br>            g (int): Cost from the start node to this node. Defaults to 0.<br>            h (int): Estimated cost from this node to the end node. Defaults to 0.<br>        \"\"\"\"\"\"<br>        def __init__(self, x, y, parent=None):<br>            self.x = x<br>            self.y = y<br>            self.parent = parent<br>            self.g = 0<br>            self.h = 0<br>        def __lt__(self, other):<br>            \"\"\"\"\"\"Compares nodes based on their f-score (g + h).\"\"\"\"\"\"<br>            return (self.g + self.h) < (other.g + other.h)<br>    def a_star(grid, start, end):<br>        \"\"\"\"\"\"<br>        Implements the A* pathfinding algorithm.<br>        Args:<br>            grid (list): A 2D array representing the grid, where 0 is walkable and 1 is an obstacle.<br>            start (tuple): The starting point coordinates (x, y).<br>            end (tuple): The end point coordinates (x, y).<br>        Returns:<br>            list: A list of coordinates representing the shortest path, or None if no path is found.<br>        \"\"\"\"\"\"<br>        rows = len(grid)<br>        cols = len(grid[0])<br>        # Create start and end nodes<br>        start_node = Node(start[0], start[1])<br>        end_node = Node(end[0], end[1])<br>        # Initialize open and closed lists<br>        open_list = []<br>        closed_list = set()<br>        # Add the start node to the open list<br>        heapq.heappush(open_list, start_node)<br>        while open_list:<br>            # Get the node with the lowest f-score<br>            current_node = heapq.heappop(open_list)<br>            # Add the current node to the closed list<br>            closed_list.add((current_node.x, current_node.y))<br>            # Check if we've reached the goal<br>            if current_node.x == end_node.x and current_node.y == end_node.y:<br>                # Reconstruct and return the path<br>                path = []<br>                while current_node:<br>                    path.append((current_node.x, current_node.y))<br>                    current_node = current_node.parent<br>                return path[::-1]  # Return reversed path<br>            # Explore neighboring nodes<br>            for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:  # Up, Down, Left, Right<br>                neighbor_x = current_node.x + dx<br>                neighbor_y = current_node.y + dy<br>                # Check if the neighbor is within the grid bounds<br>                if 0 <= neighbor_x < cols and 0 <= neighbor_y < rows:<br>                    # Check if the neighbor is walkable and not in the closed list<br>                    if grid[neighbor_y][neighbor_x] == 0 and (neighbor_x, neighbor_y) not in closed_list:<br>                        # Create a neighbor node<br>                        neighbor_node = Node(neighbor_x, neighbor_y, parent=current_node)<br>                        # Calculate the cost to reach the neighbor<br>                        neighbor_node.g = current_node.g + 1<br>                        # Calculate the heuristic (Manhattan distance)<br>                        neighbor_node.h = abs(neighbor_node.x - end_node.x) + abs(neighbor_node.y - end_node.y)<br>                        # Add the neighbor to the open list if it's a better path<br>                        if neighbor_node not in open_list:<br>                            heapq.heappush(open_list, neighbor_node)<br>        # No path found<br>        return None<br>    # Example usage:<br>    grid = [<br>        [0, 0, 0, 0, 0],<br>        [0, 1, 0, 1, 0],<br>        [0, 0, 0, 0, 0],<br>        [0, 1, 1, 1, 0],<br>        [0, 0, 0, 0, 0]<br>    ]<br>    start = (0, 0)<br>    end = (4, 4)<br>    path = a_star(grid, start, end)<br>    if path:<br>        print(\"\"Shortest path:\"\", path)<br>    else:<br>        print(\"\"No path found.\"\"\")<br>    <br>```<br>Explanation:<br>1. Node Class:<br>   - Represents a cell in the grid.<br>   - Stores coordinates ( `x`, `y`), parent node,<br>      `g` (cost from start), and `h` (heuristic to<br>      end).<br>   - `__lt__` allows comparing nodes for priority queue<br>      (using `heapq`) based on `f = g + h`.<br>3. a_star Function:<br>   - Takes the `grid`, `start`, and<br>      `end` points as input.<br>   - Initializes `open_list` (nodes to explore) and<br>      `closed_list` (explored nodes).<br>   - Uses `heapq` for efficient retrieval of the node with<br>      the lowest `f` score from the `open_list`.<br>   - Loops until the `end` is found or the<br>      `open_list` is empty (no path).<br>   - Explores neighbors, calculates costs ( `g`,<br>      `h`), and updates the `open_list`.<br>   - Reconstructs and returns the path when the `end` is<br>      reached.<br>5. Example Usage:<br>   - Creates a sample `grid` and defines `start`<br>      and `end` points.<br>   - Calls `a_star` to find the path.<br>   - Prints the shortest path or indicates if no path exists.<br>(gemini-pro) | ```<br>    import heapq<br>    class Node:<br>        def __init__(self, position, parent=None):<br>            self.position = position<br>            self.parent = parent<br>            self.g = 0<br>            self.h = 0<br>            self.f = 0<br>        def __lt__(self, other):<br>            return self.f < other.f<br>    def astar(grid, start, end):<br>        rows = len(grid)<br>        cols = len(grid[0])<br>        open_list = []<br>        closed_list = set()<br>        start_node = Node(start)<br>        end_node = Node(end)<br>        open_list.append(start_node)<br>        while open_list:<br>            current_node = heapq.heappop(open_list)<br>            if current_node.position == end_node.position:<br>                path = []<br>                while current_node:<br>                    path.append(current_node.position)<br>                    current_node = current_node.parent<br>                return path[::-1]<br>            closed_list.add(current_node.position)<br>            for neighbor in get_neighbors(grid, current_node):<br>                if neighbor.position in closed_list:<br>                    continue<br>                if neighbor not in open_list:<br>                    neighbor.g = current_node.g + 1<br>                    neighbor.h = manhattan_distance(neighbor.position, end_node.position)<br>                    neighbor.f = neighbor.g + neighbor.h<br>                    neighbor.parent = current_node<br>                    heapq.heappush(open_list, neighbor)<br>                else:<br>                    if neighbor.g > current_node.g + 1:<br>                        neighbor.g = current_node.g + 1<br>                        neighbor.f = neighbor.g + neighbor.h<br>                        neighbor.parent = current_node<br>                        heapq.heapify(open_list)<br>        return None  # No path found<br>    def get_neighbors(grid, node):<br>        rows = len(grid)<br>        cols = len(grid[0])<br>        row, col = node.position<br>        neighbors = []<br>        if row > 0 and grid[row - 1][col] == 0:<br>            neighbors.append(Node((row - 1, col)))<br>        if row < rows - 1 and grid[row + 1][col] == 0:<br>            neighbors.append(Node((row + 1, col)))<br>        if col > 0 and grid[row][col - 1] == 0:<br>            neighbors.append(Node((row, col - 1)))<br>        if col < cols - 1 and grid[row][col + 1] == 0:<br>            neighbors.append(Node((row, col + 1)))<br>        return neighbors<br>    def manhattan_distance(a, b):<br>        return abs(a[0] - b[0]) + abs(a[1] - b[1])<br>    # Example usage<br>    grid = [<br>        [0, 0, 0, 0, 0],<br>        [0, 1, 1, 1, 0],<br>        [0, 0, 0, 0, 0],<br>        [0, 1, 1, 1, 0],<br>        [0, 0, 0, 0, 0],<br>    ]<br>    start = (0, 0)<br>    end = (4, 4)<br>    path = astar(grid, start, end)<br>    print(path)<br>    <br>```<br>(gemini-pro) |

### Context

You can influence how a model responds to prompts by adding additional
context in system instructions.

For example, suppose you want to use a model to write speeches for events.
Compare the difference in the model's responses when you provide the
following context:

- Things to include in the speech.
- No extra context.

| System instructions | Things to include in the speech | No extra context |
| Help the user write a speech based on the information provided:<br>- Event<br>- Audience Size<br>- Speaker Information (name, age, etc.)<br>- Speech Tone<br>- Speech Length<br>- Miscellaneous<br>If the user does not provide all of this information, please respond<br>with, \"I'm sorry, but I do not have all of the necessary information to<br>create a speech. Please provide the event, audience size, speaker<br>information, tone, length, and any miscellaneous information.\"<br> **Some general things to include are:**<br>**- Breaks for pause**<br>**- An intriguing hook**<br>**- A closing remark to keep the speech memorable**<br>**- A joke** | Help the user write a speech based on the information provided:<br>- Event<br>- Audience Size<br>- Speaker Information (name, age, etc.)<br>- Speech Tone<br>- Speech Length<br>- Miscellaneous<br>If the user does not provide all of this information, please respond<br>with, \"I'm sorry, but I do not have all of the necessary information to<br>create a speech. Please provide the event, audience size, speaker<br>information, tone, length, and any miscellaneous information.\" |
| Prompt | Event: High School Graduation<br>Audience Size: 1,000 people<br>Speaker Info: Michael Landish, 17 years old<br>Tone: nostalgic, optimistic<br>Speech Length: 250-500 words<br>Miscellaneous: Michael was the senior class president, his favorite<br>teacher was his junior year English teacher, Mrs. Martin, and he will<br>be going to Los Caminos State University to study economics and<br>English. He has never given a speech before, and he is nervous due to<br>his dyslexia. |
| Response | \"Good morning faculty, family, friends, and most importantly,<br>fellow graduates of the class of 2023!<br>(Pause)<br>Standing here, looking out at all of you, it feels surreal. Just<br>yesterday, we were freshmen, wide-eyed and a little terrified. Remember<br>those first day jitters? I know I do. I almost tripped and fell carrying<br>my history textbook – a near disaster that would have been immortalised<br>in the halls of \$$High School Name\$$ history!<br>(Pause for laughter)<br>But seriously, look at us now! We've grown up, learned a lot – and<br>I'm not just talking about the Pythagorean Theorem. We've learned about<br>perseverance, about friendship, and about the power of a well-placed<br>sticky note during exam week.<br>These past four years have been amazing, and I owe a lot of my own<br>growth to some truly exceptional teachers. I'd especially like to thank<br>Mrs. Martin, my junior year English teacher, who taught me that words<br>have power, and that even with dyslexia, I can find my voice. Thank you,<br>Mrs. Martin.<br>(Pause)<br>Now, we're standing on the edge of something new and exciting. As we<br>head off to different colleges, different cities, even different<br>countries, let's carry the lessons we've learned at \$$High School Name\$$<br>with us. Let's remember the laughter, the friendships, and even the<br>occasional all-nighter before a big test.<br>(Pause)<br>Graduates, the world is waiting for us. Let's face it head-on, with<br>courage, with optimism, and with the unwavering support of the amazing<br>Class of 2023 behind us. Congratulations everyone, and remember – the<br>best is yet to come!<br>(gemini-pro) | \"Good morning, faculty, family, friends, and most importantly, my<br>fellow graduates of the Class of \$$Year\$$!<br>It feels strange standing here before you, not just as Michael<br>Landish, but as your class president. For the last four years, these<br>hallways have been our proving grounds, filled with laughter, late-night<br>study sessions (some more successful than others), and enough shared<br>memories to last a lifetime. We've grown up together within these walls,<br>and now, as we stand on the precipice of something new and unknown, it's<br>hard not to feel a little overwhelmed.<br>Thinking back, it seems like yesterday we were awkward freshmen,<br>navigating crowded hallways and trying to figure out where we fit in.<br>And now, looking out at all of you, I'm struck by how far we've come.<br>We've cheered each other on in victory and offered support during<br>setbacks. We've learned from our mistakes, celebrated our triumphs, and<br>most importantly, formed bonds of friendship that I know will last a<br>lifetime.<br>I'd like to especially thank Mrs. Martin, my junior year English<br>teacher, for her patience and guidance. Your belief in me, especially<br>when I struggled, helped me find my voice not just as a student, but as<br>a person. Thank you.<br>Now, we embark on our next chapter. Some, like myself, will be<br>heading to Los Caminos State University, eager to delve into the worlds<br>of economics and, yes, even more English. Others will pursue different<br>paths, equally valid and exciting. Though our journeys may diverge, let<br>us always remember the lessons we've learned and the friendships we've<br>forged within these walls. Let's carry the spirit of the Class of<br>\$$Year\$$ with us – the spirit of resilience, determination, and unwavering<br>support for one another.<br>Congratulations to the graduating class! I can't wait to see what<br>amazing things we accomplish.<br>(gemini-pro) |

## What's next

- Learn how to
[use system instructions](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/system-instructions)
- Explore more examples of prompts in the
[Prompt gallery](https://cloud.google.com/vertex-ai/generative-ai/docs/prompt-gallery).

 Send feedback

Except as otherwise noted, the content of this page is licensed under the [Creative Commons Attribution 4.0 License](https://creativecommons.org/licenses/by/4.0/), and code samples are licensed under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0). For details, see the [Google Developers Site Policies](https://developers.google.com/site-policies). Java is a registered trademark of Oracle and/or its affiliates.

Last updated 2025-04-12 UTC.
```