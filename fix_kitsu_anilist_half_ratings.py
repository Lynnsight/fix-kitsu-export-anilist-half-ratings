import requests
import time

KITSU_TOKEN = ""    # Relatively short.
ANILIST_TOKEN = ""    # This is a JWT so it is very long.

KITSU_HEADERS = {
    "Accept": "application/vnd.api+json",
    "Content-Type": "application/vnd.api+json",
    "Authorization": f"Bearer {KITSU_TOKEN}"
}

ANILIST_HEADERS = {"Authorization": f"Bearer {ANILIST_TOKEN}"}

KITSU_USER_ID = 0    # Replace with your Kitsu user ID, obtained via api.


def fetch_kitsu_library(user_id):
    results = []
    url = f"https://kitsu.io/api/edge/library-entries?filter[user_id]={user_id}&page[limit]=20&include=anime"

    while url:
        res = requests.get(url, headers=KITSU_HEADERS)
        res.raise_for_status()
        data = res.json()

        for entry in data['data']:
            rating = entry['attributes'].get('ratingTwenty')
            if rating and rating % 2 == 1:    # Check if rating is a half-point (1, 3, 5, ..., 19):
                anime_id = entry['relationships']['anime']['data']['id']
                results.append((anime_id, float(rating / 2)))

        url = data.get('links', {}).get('next')

    return results


def get_kitsu_mal_id(anime_id):
    url = f"https://kitsu.io/api/edge/anime/{anime_id}/mappings"
    res = requests.get(url, headers=KITSU_HEADERS)
    if res.status_code != 200:
        print(f"❌ Error {res.status_code} getting mappings for anime {anime_id}")
        return None

    mappings = res.json().get('data', [])
    for mapping in mappings:
        attr = mapping['attributes']
        if attr['externalSite'] == 'myanimelist/anime':
            return int(attr['externalId'])

    print(f"⚠️ No MAL ID found for anime {anime_id}")
    return None


def post_with_retry(url, json, headers=None, max_retries=5):
    for attempt in range(max_retries):
        response = requests.post(url, json=json, headers=headers)

        # If OK, return
        if response.status_code < 400:
            return response

        # Handle rate limiting
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 2))    # fallback to 2s
            print(f"Rate limited. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
            continue

        # Other errors
        print(f"Request failed (status {response.status_code}): {response.text}")
        break

    raise Exception(f"Failed after {attempt} retries")


def search_anilist_by_mal_id(mal_id):
    """Search AniList entry by MAL ID."""
    query = '''
    query ($idMal: Int) {
      Media(idMal: $idMal, type: ANIME) {
        id
        title {
          romaji
        }
      }
    }
    '''
    variables = {'idMal': mal_id}
    res = post_with_retry('https://graphql.anilist.co',
                          json={
                              'query': query,
                              'variables': variables
                          },
                          headers=ANILIST_HEADERS)
    try:
        return res.json()['data']['Media']['id']
    except:
        print(f"❌ Error searching AniList for MAL ID {mal_id}: {res.text}")
        return None


def update_anilist_score(anilist_id, score):
    """Submit score to AniList"""
    mutation = '''
    mutation ($mediaId: Int, $score: Float) {
      SaveMediaListEntry(mediaId: $mediaId, score: $score) {
        id
        score
      }
    }
    '''
    variables = {'mediaId': anilist_id, 'score': score}
    res = post_with_retry('https://graphql.anilist.co',
                          json={
                              'query': mutation,
                              'variables': variables
                          },
                          headers=ANILIST_HEADERS)
    return res.status_code == 200


def main():
    entries = fetch_kitsu_library(KITSU_USER_ID)
    print(f"Found {len(entries)} decimal-rated anime entries on Kitsu.")

    for anime_id, rating in entries:
        print(f"➡ Processing rating {rating} for {anime_id}")

        mal_id = get_kitsu_mal_id(anime_id)
        if not mal_id:
            print("⚠️  No MAL ID found for this anime. Skipping.")
            continue

        anilist_id = search_anilist_by_mal_id(mal_id)
        if not anilist_id:
            continue

        success = update_anilist_score(anilist_id, rating)
        if success:
            print(f"✅ Updated AniList rating for {anilist_id} to {rating}")
        else:
            print(f"❌ Failed to update AniList rating for media ID {anilist_id}")


if __name__ == "__main__":
    main()
