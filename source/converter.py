"""This script converst the KAAA Thesuarus in a CSV file in ISO 2788 form to RDF in the Turtle format,
conformant with the VocPub profile of the SKOS vocabulary model.

(c) KurrawongAI, 2024

Contact Nicholas Car (nick@kurrawong.ai) for any issues/queries.
"""

import csv
from collections import Counter
from datetime import datetime

from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import SKOS, RDF

KAAA = Namespace("https://linked.data.gov.au/def/kaaa/")
CS = URIRef(str(KAAA).rstrip("/"))

definitions = {}


def get_unique_codes():
    codes = set()
    with open("KAAA.csv") as f:
        txt_data = f.readlines()
        for line in txt_data:
            if line != "\n":
                words = line.split(",")
                code = words[0].replace('"', "")
                codes.add(code)
    return codes


"""
Counter(
    {
        'BT': 1540, 
        'NT': 1540, 
        'SN': 1285, 
        'ST': 850, 
        'RT': 566, 
        'KW': 562, 
        'UF': 454
    })
"""


def count_unique_codes():
    codes = []
    with open("KAAA.csv") as f:
        txt_data = f.readlines()
        for line in txt_data:
            if line != "\n":
                words = line.split(",")
                codes.append(words[0].replace('"', ""))

    return Counter(codes)


def make_concept_iri(code: str) -> URIRef:
    s = code.lower().strip()
    removable_chars = ["(", ")"]
    for c in removable_chars:
        s = s.replace(c, "")

    replacable_chars = [" "]
    for c in replacable_chars:
        s = s.replace(c, "-")

    replacable_chars2 = ["&"]
    for c in replacable_chars2:
        s = s.replace(c, "and")

    return URIRef("https://linked.data.gov.au/def/kaaa/" + s)


def process_KW(g, value) -> URIRef:
    iri = make_concept_iri(value)
    g.add((
        iri,
        RDF.type,
        SKOS.Concept
    ))
    g.add((
        iri,
        SKOS.inScheme,
        CS
    ))
    g.add((
        iri,
        SKOS.prefLabel,
        Literal(value, lang="en")
    ))

    return iri


def process_BT(g, value, concept_iri):
    g.add((
        concept_iri,
        SKOS.broader,
        make_concept_iri(value)
    ))


def process_NT(g, value, concept_iri):
    g.add((
        concept_iri,
        SKOS.narrower,
        make_concept_iri(value)
    ))


def process_SN(g, value, concept_iri):
    if concept_iri is not None:
        if definitions.get(concept_iri) is None:
            definitions[concept_iri] = value
        else:
            definitions[concept_iri] = definitions[concept_iri] + " " + value

        g.remove((
            concept_iri,
            SKOS.definition,
            None
        ))
        g.add((
            concept_iri,
            SKOS.definition,
            Literal(definitions[concept_iri], lang="en")
        ))


def process_ST(g, value, concept_iri):
    if concept_iri is None:
        pass
    else:
        g.add((
            concept_iri,
            SKOS.altLabel,
            Literal(value)
        ))


def process_RT(g, value, concept_iri):
    g.add((
        concept_iri,
        SKOS.related,
        make_concept_iri(value)
    ))


def process_UF(g, value, concept_iri):
    pass


def generate_graph(kaaa_file) -> Graph:
    g = Graph()
    g.bind("", KAAA)
    g.bind("cs", KAAA.rstrip("/"))

    with open(kaaa_file) as f:
        csv_data = csv.reader(f)
        concept_iri = None
        for line in csv_data:
            if len(line) < 1:
                concept_iri = None
                value = None
            else:
                value = line[1].strip()
                if line[0].startswith("KW"):
                    concept_iri = process_KW(g, value)
                elif line[0].startswith("BT"):
                    process_BT(g, value, concept_iri)
                elif line[0].startswith("NT"):
                    process_NT(g, value, concept_iri)
                elif line[0].startswith("SN"):
                    process_SN(g, value, concept_iri)
                elif line[0].startswith("ST"):
                    process_ST(g, value, concept_iri)
                elif line[0].startswith("RT"):
                    process_RT(g, value, concept_iri)
                elif line[0].startswith("UF"):
                    process_UF(g, value, concept_iri)

    return g


def expand_graph(g: Graph):
    for s in g.subjects(RDF.type, SKOS.Concept):
        no_broader = True
        for o in g.objects(s, SKOS.broader):
            no_broader = False

        if no_broader:
            g.add((
                CS,
                SKOS.hasTopConcept,
                s
            ))
            g.add((
                s,
                SKOS.topConceptOf,
                CS
            ))

    for s in g.subjects(RDF.type, SKOS.Concept):
        if not g.value(s, SKOS.definition):
            g.add((
                s,
                SKOS.definition,
                g.value(s, SKOS.prefLabel)
            ))


def add_cs_metadata(g):
    g += Graph().parse(data=f"""
    PREFIX : <{KAAA}>
    PREFIX rstatus: <https://linked.data.gov.au/def/reg-statuses/>
    PREFIX dcat: <http://www.w3.org/ns/dcat#>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX isoroles: <http://def.isotc211.org/iso19115/-1/2018/CitationAndResponsiblePartyInformation/code/CI_RoleCode/>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX reg: <http://purl.org/linked-data/registry#>
    PREFIX schema: <https://schema.org/>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    
    <{CS}>
        a skos:ConceptScheme ;
        schema:dateCreated "2020-05-11"^^xsd:date ;
        schema:creator <https://linked.data.gov.au/org/nsw-sara> ;
        schema:contributor <https://kurrawong.ai> ;
        schema:dateModified "{datetime.now().strftime('%Y-%m-%d')}"^^xsd:date ;
        # schema:publisher <> ;
        owl:versionIRI :1 ;
        owl:versionInfo "1" ;
        reg:status rstatus:stable ; 
        schema:license <https://purl.org/NET/rdflicense/cc-by-nc-sa4.0> ;
        schema:copyrightNotice "(c) State of New South Wales through the State Archives and Records Authority of NSW 2022" ;
        skos:definition ""@en ;
        skos:prefLabel "Keyword AAA Thesaurus"@en ;
        skos:historyNote "This vocabulary is a direct ISO 2788 -> SKOS RDF conversion of the KAAA Thesuarus as provided by NSW State Archives and Records Authority" ; 
    .
    
    <https://linked.data.gov.au/org/nsw-sara>
        a schema:Organization ;
        schema:name "KurrawongAI" ;
        schema:url "https://kurrawong.ai"^^xsd:anyURI ;
    .    
    
    <https://kurrawong.ai>
        a schema:Organization ;
        schema:name "State Archives and Records Authority of NSW" ;
        schema:url "https://kurrawong.ai"^^xsd:anyURI ;
    .
    """)
    g.bind("rstatus", Namespace("https://linked.data.gov.au/def/reg-statuses/"))
    g.bind("reg", Namespace("http://purl.org/linked-data/registry#"))


if __name__ == "__main__":
    # print(get_unique_codes())

    # print(count_unique_codes())
    g = generate_graph("KAAA.csv")
    expand_graph(g)
    add_cs_metadata(g)

    g.serialize(destination="../kaaa.ttl", format="longturtle")
