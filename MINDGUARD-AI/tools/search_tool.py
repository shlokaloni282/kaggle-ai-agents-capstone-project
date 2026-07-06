from duckduckgo_search import DDGS


def search_resources(location):

    query = f"""
    mental health helpline therapist
    {location} India
    """

    results=[]

    with DDGS() as search:

        for item in search.text(
            query,
            max_results=5
        ):

            results.append(
                item["href"]
            )

    return results