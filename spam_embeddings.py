from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
import time
from typing import List
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
spam_examples = [
    "I wanted to share something exciting with you. I've been running my online store and consistently making sales through dropshipping. It's been an incredible job and I've learned so much about choosing winning products, setting up a store, and running an effective marketing campaign. Now, I'm looking to help others who want to get started or improve their results in this business. If you're interested, I'd love to share some tips and strategies that worked for me.",
    "Dropshipping has been a game-changer in my life, my newest venture has just launched and I'm overflowing with gratitude! Now, I'm thrilled to share my knowledge with others @here",
    "Let's make $10,000 in 72 hours! I'm offering a unique chance to help 30 people, including you, earn $10,000 in just 72 hours. No upfront payment is needed—once you hit the $10,000 mark, you'll only pay me 10% of your earnings. I'll be sharing a proven, step-by-step strategy and will personally guide you to make sure you succeed. It's a risk-free way to see a real income boost fast, and I'm confident we can hit this goal together.",
    "I'm offering a unique chance to help 30 people, including you, earn $10,000 in just 72 hours. No upfront payment is needed—once you hit the $10,000 mark, you'll only pay me 10% of your earnings. I'll be sharing a proven, step-by-step strategy and will personally guide you to make sure you succeed. It's a risk-free way to see a real income boost fast, and I'm confident we can hit this goal together. I'll be sharing a proven, step-by-step strategy and will personally guide you to make sure you succeed. It's a risk-free way to see a real income boost fast, and I'm confident we can hit this goal together.",
    "Are you new to dropshipping and looking to make your first sales? I'm offering free mentoring sessions to help beginners get started and achieve their goals. Whether you're just starting out or need guidance to boost your sales, I'm here to help! Comment 'Interested' or send me a message to learn more.",
    "Dropshipping is dead? NO dropshipping is so alive that there's so many people trying to compete for that space.So in order for you to compete instead of being a little batch get really good the ones in the market that win and are the best. Winners win and losers lose,So if you're not making money in dropshipping. Bro news flash people are still buying.Dm to help you get started.",
    "HELLO GUYS🙏 Were offering a new strategies for drop shipping marketing with email extractor marketing And this strategies as bean helping a lot, Why many drop shippers are making money with it, so if you don't mind we can chat👍 👍 try to Learn more about how  to makes it easy to build an ecommerce site for dropshipping and any other kind of retail strategy and tired of searching the millions of products on AliExpress and Shopify for potential winners? Our product scraper analyzes thousands of products each day to show you which have the highest dropshipping potential💯",
    "I'm currently looking to help just 5 people kick-start their dropshipping businesses. I've seen many struggling due to lack of mentorship or overwhelmed guides, and I want to change that. With my proven marketing strategies, several clients have achieved their goals ahead of schedule, with one reaching $45K. Dropshipping has transformed student  life, growing there sales from $500 to $17,000 in two months, giving my student  the freedom to pursue there dreams. If you're serious about succeeding in dropshipping, I'm here to share effective techniques and support you. If you want to be one of the lucky 5,message me with the word 4REAL and let's get started!**",
    "Dropshipping has transformed student  life, growing there sales fr om $500 to $17,000 in two months, giving my student  the freedom to pursue there dreams. If you're serious about succeeding in dropshipping, I'm here to share effective techniques and support you. If you want to be one of the lucky 5,message me with the word '4REAL' and let's get started!**",
    "HELLO GUYS🙏 Were offering a new strategies for drop shipping marketing with email extractor marketing And this strategies as bean helping a lot, Why many drop shippers are making money with it, so if you don't mind we can chat👍 👍 try to Learn more about how  to makes it easy to build an ecommerce site for dropshipping and any other kind of retail strategy and tired of searching the millions of products on AliExpress and Shopify for potential winners? Our product scraper analyzes thousands of products each day to show you which have the highest dropshipping potential💯",
    "The best way to make online money!!! Join the business call dropshipping dropshipping is the best business ever so that you can start and it will start changing your life But the thing is that most of us might Heard about it or tried it before but failed to get it right Yes it's normal but you can be a failure if you do it yourself and you don't think of having a mentor expert who is well experienced to make it work for you And that's why I am here with opportunities for anyone who is here with a good plan to achieve from dropshipping to share them a good and the best mentor that can help them through I only need just 5 people So try your luck and secure the spot for your business success Starting me the last 2 months ago and I am now scaling up my daily profit income to $5k+",
    "I just got 10k sales today wow dropshipping is really working out for me 🤗 You can message me and I can help you coz I was in this situation of yours before ",
    "I said it before and I will say it again, I know most in here dropshop and  constantly  see people saying they make 7 figures  this and that ,however  am 21 and have made 200k in just 3 months  and would love to help some of you here so you can message me to share tips  bc I love seeing people successful in this dropshipping business with me",
    "The holiday shopping season is approaching fast, with Black Friday, Christmas, New Year's, and Valentine's Day driving increased demand for online shopping. People are ready to spend on gifts and celebrations. This is the perfect opportunity to launch your online store and capitalize on the festive spirit for profitable sales.Dm me for more tips ",
    "We have helped ecom stores scale past 6 figures and we're taking on only 3 new clients this quarter. YOU PAY ONLY AFTER RESULTS!! DM IF YOU WANT TO GROW OUR STORE.",
    "Discover the hidden secrets of the digital market that top traders don't want you to know! I'm seeking five motivated individuals who are committed to earning over $50K weekly in the digital market. Once you start seeing profits, I'll require just 10% of your earnings as my fee. Please note: I'm only interested in working with five serious and dedicated people should send me a direct message or ask me (HOW) via TELEGRAM ",
    "Can anyone help me? Can I do sales for me for free? Can I create a Shopify account? Can I supply the product? When my sales start, I will give you your money.",
    "Yoo my people, how y'all doing Who needs help starting dropshipping business?",
    "I'm excited to share that my  business has reached new heights! 🚀 When I first started, I had no idea how dropshipping worked and faced many challenges. But with persistence, I've managed to achieve remarkable results and my  Consistently hitting is over $5k on my weekly basis while my brand is now well-recognized and trusted in my niche, which was satisfied with all my customers. but The journey wasn't easy, but learning from mistakes and continuously improving has paid off. I'm here to share my tips and insights with you all to help you succeed too. Let's keep pushing forward and achieving great things together! 🌟💪"


]


OPENAI_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_KEY = os.getenv("PINECONE_API_KEY")
pc = Pinecone(api_key=PINECONE_KEY)



async def add_spam_examples_to_pinecone(messages: List[str], openai_key: str, 
                                      pinecone_key: str, 
                                      index_name: str = "spam-detection"):
    """
    Add spam examples to Pinecone index using OpenAI embeddings.
    
    Args:
        messages: List of spam message examples
        openai_key: OpenAI API key
        pinecone_key: Pinecone API key
        pinecone_env: Pinecone environment
        index_name: Name of the Pinecone index
    """
    # Initialize OpenAI and Pinecone
    print("Initializing OpenAI and Pinecone")
    print(openai_key)
    print(pinecone_key)
    client = OpenAI(api_key=openai_key)
    

    # Get index
    index = pc.Index(index_name)
    
    # Process messages in batches to avoid rate limits
    batch_size = 100
    for i in range(0, len(messages), batch_size):
        batch = messages[i:i + batch_size]
        
        try:
            embedding_response = client.embeddings.create(
                model="text-embedding-3-large",
                input=batch
            )
            
            # Prepare vectors in the correct format
            vectors = []
            for j, embedding in enumerate(embedding_response.data):
                vectors.append({
                    "id": f"spam_{i+j}",
                    "values": embedding.embedding,
                    "metadata": {"text": batch[j]}
                })
            
            # Upsert to Pinecone with the correct format
            index.upsert(vectors=vectors)
            
            print(f"Processed batch {i//batch_size + 1}, vectors {i} to {min(i+batch_size, len(messages))}")
            time.sleep(1)
            
        except Exception as e:
            print(f"Error processing batch starting at index {i}: {e}")
            continue
    
    print(f"Successfully added {len(messages)} messages to Pinecone index")


async def query_spam_similarity(message: str, openai_key: str, 
                              index_name: str = "discord-spam", 
                              top_k: int = 3) -> List[dict]:
    """
    Query Pinecone index to find similar spam messages.
    
    Args:
        message: Message to check for spam similarity
        openai_key: OpenAI API key
        index_name: Name of the Pinecone index
        top_k: Number of similar messages to return
        
    Returns:
        List of dictionaries containing similar messages and their scores
    """
    # Initialize OpenAI client
    client = OpenAI(api_key=openai_key)
    
    # Get message embedding
    embedding_response = client.embeddings.create(
        model="text-embedding-3-large",
        input=message
    )
    
    # Get the embedding vector
    query_vector = embedding_response.data[0].embedding
    
    # Query Pinecone
    index = pc.Index(index_name)
    results = index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True
    )
  
    
    return results.matches


async def test_query():
    test_message = "I’m tired of watching others win in e-commerce while I’m in stuck and I decided to start the business and now others would also watch me winning and start wishing without taking any step now"
    results = await query_spam_similarity(
        message=test_message,
        openai_key=OPENAI_KEY
    )
    
    # Print results
    print("\nSimilar spam messages:")
    for match in results:
        print(f"Score: {match.score}")
        print(f"Text: {match.metadata['text']}\n")


async def main():
    await add_spam_examples_to_pinecone(
        messages=spam_examples,
        openai_key=OPENAI_KEY,
        pinecone_key=PINECONE_KEY,
   
        index_name="discord-spam"
    )

if __name__ == "__main__":
    asyncio.run(test_query())
    # asyncio.run(main())
