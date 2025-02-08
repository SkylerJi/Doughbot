from transformers import pipeline
from PIL import Image, ImageFile
from openai import OpenAI
from spam_embeddings import query_spam_similarity

ImageFile.LOAD_TRUNCATED_IMAGES = True

vqa_pipeline = pipeline("visual-question-answering")

async def image_is_safe(sensitivity):
    image = Image.open("toModerate.jpeg")
    question = "Does the image contain pornographic, adult, gore, sexual, or other NSFW content?"
    sensitivity = 1 - sensitivity
    result = vqa_pipeline(image, question, top_k=1)[0]
    answer = result["answer"].lower()

    print(result)

    if result["score"] > sensitivity and answer.startswith("y"):
        return False
    elif result["score"] < sensitivity and answer.startswith("n"):
        return False
    return True

async def message_is_safe(message: str, apikey: str) -> bool:
    client = OpenAI(api_key=apikey)
    SIMILARITY_THRESHOLD = 0.475  # Adjust this threshold as needed
    try:
        # First check with standard moderation API
        mod_response = client.moderations.create(input=message)
        if mod_response.results[0].flagged:
            return False
            
        # Query for similar spam messages
        similar_messages = await query_spam_similarity(
            message=message,
            openai_key=apikey,
            top_k=1
        )
        
        # Check if the most similar message exceeds our threshold
        if similar_messages and similar_messages[0].score >= SIMILARITY_THRESHOLD:
            return False  # Message is too similar to known spam
            
        return True
            

        # Then apply custom rules using chat completion
        # chat_response = client.chat.completions.create(
        #     model="gpt-4o-mini",
        #     messages=[
        #         {"role": "system", "content": """You are a content moderator for an ecommerce discord server. Your goal is to get rid of spammers and bots. 
        #         Respond with only 'true' if the message is safe, or 'false' if it violates:
        #         Advertising of Ecommerce or other services. Examples include selling things or asking people to dm them to learn more. Don't be too harsh, as some people are there to learn, but if it's obvious that the message is spam, get rid of it.
        #          Please keep in mind that you're only being passed one message at a time, so many of the messages, without context, may seem like spam but in reality are just responses to other messages. Only flag the messages that are standalone spam messages, think whole paragraphs, etc."""},
        #         {"role": "user", "content": message}
        #     ],
        #     temperature=0
        # )
        
        # return chat_response.choices[0].message.content.strip().lower() == 'true'
    except Exception as e:
        print(f"Error in message moderation: {e}")
        return await message_is_safe(message, apikey)
    

