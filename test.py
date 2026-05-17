from google import genai

client = genai.Client(
    api_key="AIzaSyBakJQTISfFlnwoDLcIJPLChm72EM_G0ig"
)

response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="hello"
)

print(response.text)