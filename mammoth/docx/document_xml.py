from .. import documents
from .. import results
from .. import lists
from .xmlparser import node_types


def read_document_xml_element(element, numbering=None):
    reader = _create_reader(numbering)
    return reader(element)

def _create_reader(numbering):
    _handlers = {}
    _ignored_elements = set([
        "w:bookmarkStart",
        "w:bookmarkEnd",
        "w:sectPr",
        "w:proofErr",
        "w:lastRenderedPageBreak",
        "w:commentRangeStart",
        "w:commentRangeEnd",
        "w:commentReference",
        "w:del"
    ])

    def handler(name):
        def add(func):
            _handlers[name] = func
            
        return add

    @handler("w:t")
    def text(element):
        return results.success(documents.Text(_inner_text(element)))


    @handler("w:r")
    def run(element):
        properties = element.find_child_or_null("w:rPr")
        style_name = properties \
            .find_child_or_null("w:rStyle") \
            .attributes.get("w:val")
        is_bold = properties.find_child("w:b")
        is_italic = properties.find_child("w:i")
        
        return _read_xml_elements(element.children) \
            .map(lambda children: documents.run(
                children=children,
                style_name=style_name,
                is_bold=is_bold,
                is_italic=is_italic,
            ))


    @handler("w:p")
    def paragraph(element):
        properties = element.find_child_or_null("w:pPr")
        style_name = properties \
            .find_child_or_null("w:pStyle") \
            .attributes.get("w:val")
        numbering_properties = properties.find_child("w:numPr")
        if numbering_properties is None:
            numbering = None
        else:
            numbering = _read_numbering_properties(numbering_properties)
        
        return _read_xml_elements(element.children) \
            .map(lambda children: documents.paragraph(
                children=children,
                style_name=style_name,
                numbering=numbering,
            ))

    def _read_numbering_properties(element):
        num_id = element.find_child("w:numId").attributes["w:val"]
        level_index = element.find_child("w:ilvl").attributes["w:val"]
        return numbering.find_level(num_id, level_index)


    @handler("w:body")
    def body(element):
        return _read_xml_elements(element.children)


    @handler("w:document")
    def document(element):
        body_element = _find_child(element, "w:body")
        return _read_xml_elements(body_element.children) \
            .map(documents.document)
    
    
    @handler("w:tab")
    def tab(element):
        return results.success(documents.tab())
        
    @handler("w:ins")
    def ins(element):
        return _read_xml_elements(element.children)
    
    def read(element):
        handler = _handlers.get(element.name)
        if handler is None:
            if element.name not in _ignored_elements:
                warning = results.warning("An unrecognised element was ignored: {0}".format(element.name))
                return results.Result(None, [warning])
            else:
                return results.success(None)
        else:
            return handler(element)
        

    def _read_xml_elements(elements):
        return results.combine(map(read, elements)) \
            .map(lambda values: lists.collect(values))
    
    return read


def _find(predicate, iterable):
    for item in iterable:
        if predicate(item):
            return item


def _find_child(element, name):
    return _find(lambda child: child.name == name, element.children)


def _inner_text(node):
    if node.node_type == node_types.text:
        return node.value
    else:
        return "".join(_inner_text(child) for child in node.children)
