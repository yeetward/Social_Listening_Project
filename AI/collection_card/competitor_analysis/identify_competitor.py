# """
# Key Player/Competitor Identifier
# Identifies organizations, companies, and key players mentioned in text using NLP.
# """

# import spacy
# from collections import Counter
# import re
# from typing import List, Dict, Set

# class KeyPlayerIdentifier:
#     def __init__(self, model_name: str = "en_core_web_sm"):
#         """
#         Initialize the Key Player Identifier with a spaCy model.

#         Args:
#             model_name: spaCy model to use (default: en_core_web_sm)
#         """
#         try:
#             self.nlp = spacy.load(model_name)
#         except OSError:
#             print(f"Model '{model_name}' not found. Downloading...")
#             import subprocess
#             subprocess.run(["python", "-m", "spacy", "download", model_name])
#             self.nlp = spacy.load(model_name)

#     def identify_key_players(self, text: str) -> Dict[str, List[Dict]]:
#         """
#         Identify key players (organizations, people, products) from text.

#         Args:
#             text: Input text to analyze

#         Returns:
#             Dictionary containing identified entities by category
#         """
#         doc = self.nlp(text)

#         entities = {
#             'organizations': [],
#             'people': [],
#             'products': [],
#             'locations': [],
#             'other': []
#         }

#         entity_counts = Counter()

#         for ent in doc.ents:
#             entity_info = {
#                 'text': ent.text,
#                 'label': ent.label_,
#                 'start': ent.start_char,
#                 'end': ent.end_char
#             }

#             # Categorize entities
#             if ent.label_ in ['ORG', 'COMPANY']:
#                 entities['organizations'].append(entity_info)
#                 entity_counts[ent.text] += 1
#             elif ent.label_ in ['PERSON']:
#                 entities['people'].append(entity_info)
#                 entity_counts[ent.text] += 1
#             elif ent.label_ in ['PRODUCT']:
#                 entities['products'].append(entity_info)
#                 entity_counts[ent.text] += 1
#             elif ent.label_ in ['GPE', 'LOC']:
#                 entities['locations'].append(entity_info)
#             else:
#                 entities['other'].append(entity_info)

#         # Remove duplicates while preserving order
#         for category in entities:
#             seen = set()
#             unique_entities = []
#             for entity in entities[category]:
#                 if entity['text'] not in seen:
#                     seen.add(entity['text'])
#                     unique_entities.append(entity)
#             entities[category] = unique_entities

#         return entities

#     def rank_key_players(self, text: str, top_n: int = 10) -> List[Dict]:
#         """
#         Identify and rank key players by frequency and importance.

#         Args:
#             text: Input text to analyze
#             top_n: Number of top players to return

#         Returns:
#             List of top key players ranked by mentions
#         """
#         doc = self.nlp(text)

#         entity_counts = Counter()
#         entity_details = {}

#         for ent in doc.ents:
#             if ent.label_ in ['ORG', 'COMPANY', 'PERSON', 'PRODUCT']:
#                 entity_counts[ent.text] += 1
#                 if ent.text not in entity_details:
#                     entity_details[ent.text] = {
#                         'type': ent.label_,
#                         'contexts': []
#                     }

#                 # Get context around the entity
#                 start = max(0, ent.start - 5)
#                 end = min(len(doc), ent.end + 5)
#                 context = doc[start:end].text
#                 entity_details[ent.text]['contexts'].append(context)

#         # Create ranked list
#         ranked_players = []
#         for entity, count in entity_counts.most_common(top_n):
#             ranked_players.append({
#                 'name': entity,
#                 'mentions': count,
#                 'type': entity_details[entity]['type'],
#                 'sample_contexts': entity_details[entity]['contexts'][:3]
#             })

#         return ranked_players

#     def identify_competitors(self, text: str, company_name: str = None) -> Dict:
#         """
#         Identify potential competitors mentioned in relation to a company.

#         Args:
#             text: Input text to analyze
#             company_name: Optional company name to find competitors for

#         Returns:
#             Dictionary containing competitor information
#         """
#         entities = self.identify_key_players(text)

#         competitors = {
#             'organizations': [],
#             'competitive_keywords': []
#         }

#         # Competitive keywords to look for
#         competitive_terms = [
#             'competitor', 'rival', 'competing', 'competition',
#             'versus', 'vs', 'alternative', 'compared to', 'against'
#         ]

#         # Find organizations
#         competitors['organizations'] = entities['organizations']

#         # Find competitive mentions
#         doc = self.nlp(text.lower())
#         for token in doc:
#             if token.text in competitive_terms or token.lemma_ in competitive_terms:
#                 context_start = max(0, token.i - 10)
#                 context_end = min(len(doc), token.i + 10)
#                 context = doc[context_start:context_end].text

#                 competitors['competitive_keywords'].append({
#                     'keyword': token.text,
#                     'context': context
#                 })

#         if company_name:
#             # Filter to find organizations mentioned near the company
#             competitors['related_to_company'] = self._find_related_entities(
#                 text, company_name
#             )

#         return competitors

#     def _find_related_entities(self, text: str, company_name: str) -> List[Dict]:
#         """
#         Find entities mentioned in relation to a specific company.

#         Args:
#             text: Input text
#             company_name: Company name to search for

#         Returns:
#             List of related entities
#         """
#         doc = self.nlp(text)
#         related_entities = []

#         # Find sentences mentioning the company
#         for sent in doc.sents:
#             if company_name.lower() in sent.text.lower():
#                 # Extract other organizations from these sentences
#                 for ent in sent.ents:
#                     if ent.label_ in ['ORG', 'COMPANY'] and ent.text.lower() != company_name.lower():
#                         related_entities.append({
#                             'name': ent.text,
#                             'context': sent.text
#                         })

#         return related_entities

#     def extract_key_player_summary(self, text: str) -> Dict:
#         """
#         Generate a comprehensive summary of all key players.

#         Args:
#             text: Input text to analyze

#         Returns:
#             Comprehensive summary dictionary
#         """
#         entities = self.identify_key_players(text)
#         ranked = self.rank_key_players(text)

#         summary = {
#             'total_entities': sum(len(v) for v in entities.values()),
#             'by_category': {
#                 category: len(items) for category, items in entities.items()
#             },
#             'top_players': ranked[:5],
#             'all_entities': entities
#         }

#         return summary


# def main():
#     """Example usage of the KeyPlayerIdentifier"""

#     # Sample text
#     sample_text = """
#     Apple Inc. is facing increasing competition from Samsung and Google in the smartphone market.
#     Tim Cook, Apple's CEO, mentioned that the company is focusing on innovation.
#     Meanwhile, Microsoft under Satya Nadella is expanding its cloud services,
#     competing with Amazon Web Services and Google Cloud. Tesla, led by Elon Musk,
#     continues to dominate the electric vehicle market, but traditional automakers
#     like Ford and General Motors are catching up with their EV offerings.
#     """

#     # Initialize identifier
#     identifier = KeyPlayerIdentifier()

#     # Identify all key players
#     print("=" * 60)
#     print("KEY PLAYERS IDENTIFIED")
#     print("=" * 60)
#     entities = identifier.identify_key_players(sample_text)

#     for category, items in entities.items():
#         if items:
#             print(f"\n{category.upper()}:")
#             for item in items:
#                 print(f"  - {item['text']} ({item['label']})")

#     # Get ranked players
#     print("\n" + "=" * 60)
#     print("TOP RANKED PLAYERS")
#     print("=" * 60)
#     ranked = identifier.rank_key_players(sample_text, top_n=5)

#     for i, player in enumerate(ranked, 1):
#         print(f"\n{i}. {player['name']}")
#         print(f"   Type: {player['type']}")
#         print(f"   Mentions: {player['mentions']}")
#         print(f"   Sample context: {player['sample_contexts'][0][:80]}...")

#     # Identify competitors for Apple
#     print("\n" + "=" * 60)
#     print("COMPETITORS ANALYSIS FOR APPLE")
#     print("=" * 60)
#     competitors = identifier.identify_competitors(sample_text, "Apple")

#     print(f"\nOrganizations mentioned: {len(competitors['organizations'])}")
#     for org in competitors['organizations']:
#         print(f"  - {org['text']}")

#     if competitors.get('related_to_company'):
#         print(f"\nOrganizations mentioned with Apple:")
#         for entity in competitors['related_to_company']:
#             print(f"  - {entity['name']}")

#     # Generate summary
#     print("\n" + "=" * 60)
#     print("SUMMARY")
#     print("=" * 60)
#     summary = identifier.extract_key_player_summary(sample_text)

#     print(f"\nTotal entities found: {summary['total_entities']}")
#     print("\nBreakdown by category:")
#     for category, count in summary['by_category'].items():
#         if count > 0:
#             print(f"  {category}: {count}")


# if __name__ == "__main__":
#     main()
