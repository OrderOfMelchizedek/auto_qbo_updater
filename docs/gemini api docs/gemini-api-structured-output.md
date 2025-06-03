# Generate structured output with the Gemini API | Google AI for Developers

Gemini generates unstructured text by default, but some applications require structured text. For these use cases, you can constrain Gemini to respond with JSON, a structured data format suitable for automated processing. You can also constrain the model to respond with one of the options specified in an enum.

Here are a few use cases that might require structured output from the model:
- Build a database of companies by pulling company information out of newspaper articles.
- Pull standardized information out of resumes.
- Extract ingredients from recipes and display a link to a grocery website for each ingredient.

In your prompt, you can ask Gemini to produce JSON-formatted output, but note that the model is not guaranteed to produce JSON and nothing but JSON.

For a more deterministic response, you can pass a specific JSON schema in a [responseSchema](/api/rest/v1beta/GenerationConfig#FIELDS.response_schema) field so that Gemini always responds with an expected structure. To learn more about working with schemas, see [More about JSON schemas](#json-schemas).

This guide shows you how to generate JSON using the [generateContent](/api/rest/v1/models/generateContent) method through the SDK of your choice or using the REST API directly. The examples show text-only input, although Gemini can also produce JSON responses to multimodal requests that include [images](/gemini-api/docs/image-understanding), [videos](/gemini-api/docs/video-understanding), and [audio](/gemini-api/docs/audio).

## More about JSON schemas

When you configure the model to return a JSON response, you can use a Schema object to define the shape of the JSON data. The Schema represents a select subset of the [OpenAPI 3.0 Schema object](https://spec.openapis.org/oas/v3.0.3#schema-object).

Here's a pseudo-JSON representation of all the Schema fields:

```json
{
  "type": enum (Type),
  "format": string,
  "description": string,
  "nullable": boolean,
  "enum": [
    string
  ],
  "maxItems": string,
  "minItems": string,
  "properties": {
    string: {
      object (Schema)
    },
    ...
  },
  "required": [
    string
  ],
  "propertyOrdering": [
    string
  ],
  "items": {
    object (Schema)
  }
}
```

The Type of the schema must be one of the OpenAPI [Data Types](https://spec.openapis.org/oas/v3.0.3#data-types). Only a subset of fields is valid for each Type. The following list maps each Type to valid fields for that type:

- `string` -> enum, format
- `integer` -> format
- `number` -> format
- `boolean`
- `array` -> minItems, maxItems, items
- `object` -> properties, required, propertyOrdering, nullable

Here are some example schemas showing valid type-and-field combinations:

```json
{ "type": "string", "enum": ["a", "b", "c"] }
{ "type": "string", "format": "date-time" }
{ "type": "integer", "format": "int64" }
{ "type": "number", "format": "double" }
{ "type": "boolean" }
{ "type": "array", "minItems": 3, "maxItems": 3, "items": { "type": ... } }
{ 
  "type": "object",
  "properties": {
    "a": { "type": ... },
    "b": { "type": ... },
    "c": { "type": ... }
  },
  "nullable": true,
  "required": ["c"],
  "propertyOrdering": ["c", "b", "a"]
}
```

For complete documentation of the Schema fields as they're used in the Gemini API, see the [Schema reference](/api/caching#Schema).

## Property ordering

When you're working with JSON schemas in the Gemini API, the order of properties is important. By default, the API orders properties alphabetically and does not preserve the order in which the properties are defined (although the [Google Gen AI SDKs](/gemini-api/docs/sdks) may preserve this order). If you're providing examples to the model with a schema configured, and the property ordering of the examples is not consistent with the property ordering of the schema, the output could be rambling or unexpected.

To ensure a consistent, predictable ordering of properties, you can use the optional `propertyOrdering[]` field.

```json
"propertyOrdering": ["recipe_name", "ingredients"]
```

`propertyOrdering[]` – not a standard field in the OpenAPI specification – is an array of strings used to determine the order of properties in the response. By specifying the order of properties and then providing examples with properties in that same order, you can potentially improve the quality of results.
