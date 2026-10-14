"""
Test script
---------------------------------
This python script is used to test the inference service API.
It sends a user profile (example), candidate movies and, optionally,
an addition message. Finally, outputs the response from the API.
"""

import requests


# ================================================================================================ #
# ========== Sample data ========================================================================= #
# ================================================================================================ #
TEST_PROFILE = {
    "user_id": "u_482",
    "favorite_movie": "Arrival",
    "favorite_genres": ["sci-fi", "thriller", "mystery"],
    "favorite_actors": ["Denis Villeneuve", "Amy Adams"],
    "watch_history": [
        {"title": "Arrival", "rating": 5},
        {"title": "Prisoners", "rating": 4},
        {"title": "Sicario", "rating": 5},
        {"title": "The Notebook", "rating": 2}
    ]
}


# ================================================================================================ #
# ========== Main Function ======================================================================= #
# ================================================================================================ #
if __name__ == "__main__":
    # Make the request
    res = requests.post(
        "http://localhost:8000/recommendations/generate",
        json={
            "message": ""
        }
    )

    # Receive the response
    res.raise_for_status()
    data = res.json()
    print(data)