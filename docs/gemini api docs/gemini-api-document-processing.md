# Document understanding | Gemini API | Google AI for Developers

The Gemini API supports PDF input, including long documents (up to 3600 pages). Gemini models process PDFs with native vision, and are therefore able to understand both text and image contents inside documents. With native PDF vision support, Gemini models are able to:

- Analyze diagrams, charts, and tables inside documents
- Extract information into structured output formats
- Answer questions about visual and text contents in documents
- Summarize documents
- Transcribe document content (e.g. to HTML) preserving layouts and formatting, for use in downstream applications

This tutorial demonstrates some possible ways to use the Gemini API to process PDF documents.

## PDF input

For PDF payloads under 20MB, you can choose between uploading base64 encoded documents or directly uploading locally stored files.

### As inline data

You can process PDF documents directly from URLs. Here's a code snippet showing how to do this:

```python
from google import genai
from google.genai import types
import httpx

client = genai.Client()

doc_url = "https://discovery.ucl.ac.uk/id/eprint/10089234/1/343019_3_art_0_py4t4l_convrt.pdf"

# Retrieve and encode the PDF byte
doc_data = httpx.get(doc_url).content

prompt = "Summarize this document"

response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=[
        types.Part.from_bytes(
            data=doc_data,
            mime_type='application/pdf',
        ),
        prompt])

print(response.text)
```

## Technical details

Gemini 1.5 Pro and 1.5 Flash support a maximum of 3,600 document pages. Document pages must be in one of the following text data MIME types:

- PDF - `application/pdf`
- JavaScript - `application/x-javascript`, `text/javascript`
- Python - `application/x-python`, `text/x-python`
- TXT - `text/plain`
- HTML - `text/html`
- CSS - `text/css`
- Markdown - `text/md`
- CSV - `text/csv`
- XML - `text/xml`
- RTF - `text/rtf`

Each document page is equivalent to 258 tokens.

While there are no specific limits to the number of pixels in a document besides the model's context window, larger pages are scaled down to a maximum resolution of 3072x3072 while preserving their original aspect ratio, while smaller pages are scaled up to 768x768 pixels. There is no cost reduction for pages at lower sizes, other than bandwidth, or performance improvement for pages at higher resolution.

For best results:
- Rotate pages to the correct orientation before uploading.
- Avoid blurry pages.
- If using a single page, place the text prompt after the page.

## Locally stored PDFs

For locally stored PDFs, you can use the following approach:

```python
from google import genai
from google.genai import types
import pathlib
import httpx

client = genai.Client()

doc_url = "https://discovery.ucl.ac.uk/id/eprint/10089234/1/343019_3_art_0_py4t4l_convrt.pdf"

# Retrieve and encode the PDF byte
filepath = pathlib.Path('file.pdf')
filepath.write_bytes(httpx.get(doc_url).content)

prompt = "Summarize this document"

response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=[
        types.Part.from_bytes(
            data=filepath.read_bytes(),
            mime_type='application/pdf',
        ),
        prompt])

print(response.text)
```

## Large PDFs

You can use the File API to upload a document of any size. Always use the File API when the total request size (including the files, text prompt, system instructions, etc.) is larger than 20 MB.

Call [media.upload](/api/rest/v1beta/media/upload) to upload a file using the File API. The following code uploads a document file and then uses the file in a call to [models.generateContent](/api/generate-content#method:-models.generatecontent).

### Large PDFs from URLs

Use the File API for large PDF files available from URLs, simplifying the process of uploading and processing these documents directly through their URLs:

```python
from google import genai
from google.genai import types
import io
import httpx

client = genai.Client()

long_context_pdf_path = "https://www.nasa.gov/wp-content/uploads/static/history/alsj/a17/A17_FlightPlan.pdf"

# Retrieve and upload the PDF using the File API
doc_io = io.BytesIO(httpx.get(long_context_pdf_path).content)

sample_doc = client.files.upload(
    # You can pass a path or a file-like object here
    file=doc_io,
    config=dict(
        mime_type='application/pdf')
)

prompt = "Summarize this document"

response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=[sample_doc, prompt])

print(response.text)
```

### Large PDFs stored locally

```python
from google import genai
from google.genai import types
import pathlib
import httpx

client = genai.Client()

long_context_pdf_path = "https://www.nasa.gov/wp-content/uploads/static/history/alsj/a17/A17_FlightPlan.pdf"

# Retrieve the PDF
file_path = pathlib.Path('A17.pdf')
file_path.write_bytes(httpx.get(long_context_pdf_path).content)

# Upload the PDF using the File API
sample_file = client.files.upload(
    file=file_path,
)

prompt="Summarize this document"

response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=[sample_file, "Summarize this document"])

print(response.text)
```

You can verify the API successfully stored the uploaded file and get its metadata by calling [files.get](/api/rest/v1beta/files/get). Only the `name` (and by extension, the `uri`) are unique.

```python
from google import genai
import pathlib

client = genai.Client()

fpath = pathlib.Path('example.txt')
fpath.write_text('hello')

file = client.files.upload('example.txt')
file_info = client.files.get(file.name)

print(file_info.model_dump_json(indent=4))
```

## Multiple PDFs

The Gemini API is capable of processing multiple PDF documents in a single request, as long as the combined size of the documents and the text prompt stays within the model's context window.

```python
from google import genai
import io
import httpx

client = genai.Client()

doc_url_1 = "https://arxiv.org/pdf/2312.11805"
doc_url_2 = "https://arxiv.org/pdf/2403.05530"

# Retrieve and upload both PDFs using the File API
doc_data_1 = io.BytesIO(httpx.get(doc_url_1).content)
doc_data_2 = io.BytesIO(httpx.get(doc_url_2).content)

sample_pdf_1 = client.files.upload(
    file=doc_data_1,
    config=dict(mime_type='application/pdf')
)

sample_pdf_2 = client.files.upload(
    file=doc_data_2,
    config=dict(mime_type='application/pdf')
)

prompt = "What is the difference between each of the main benchmarks between these two papers? Output these in a table."

response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=[sample_pdf_1, sample_pdf_2, prompt])

print(response.text)
```

## What's next

To learn more, see the following resources:

- [File prompting strategies](/gemini-api/docs/files#prompt-guide): The Gemini API supports prompting with text, image, audio, and video data, also known as multimodal prompting.
- [System instructions](/gemini-api/docs/text-generation#system-instructions): System instructions let you steer the behavior of the model based on your specific needs and use cases.
