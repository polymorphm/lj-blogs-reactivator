# -*- mode: python; coding: utf-8 -*-
#
# Copyright (c) 2013, 2014 Andrej Antonov <polymorphm@gmail.com>.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

assert str is not bytes

from xml.etree import ElementTree as et

def elem_in_attrib_check(elem, attrib_name, attrib_value):
    assert isinstance(attrib_name, str)
    assert isinstance(attrib_value, str)
    
    if not isinstance(elem, et.Element):
        return False
    
    elem_attrib_value_str = elem.attrib.get(attrib_name)
    
    if elem_attrib_value_str is None:
        return False
    
    elem_attrib_value_list = elem_attrib_value_str.split()
    
    for elem_attrib_value in elem_attrib_value_list:
        if elem_attrib_value.lower() == attrib_value.lower():
            return True
    
    return False

def elem_condition_check(elem, condition):
    assert isinstance(condition, dict)
    
    if not isinstance(elem, et.Element) or not isinstance(elem.tag, str):
        return False
    
    tag = condition.get('tag')
    attrib_map = condition.get('attrib')
    in_attrib_map = condition.get('in_attrib')
    any_condition = condition.get('any')
    not_condition = condition.get('not')
    
    if tag is not None:
        assert isinstance(tag, str)
        
        if tag.lower() != elem.tag.lower():
            return False
    
    if attrib_map is not None:
        assert isinstance(attrib_map, dict)
        
        for attrib_name, attrib_value in attrib_map.items():
            assert isinstance(attrib_name, str)
            assert isinstance(attrib_value, str)
            
            elem_attrib_value = elem.attrib.get(attrib_name)
            
            if elem_attrib_value is None or \
                    elem_attrib_value.lower() != attrib_value.lower():
                return False
    
    if in_attrib_map is not None:
        assert isinstance(in_attrib_map, dict)
        
        for in_attrib_name, in_attrib_list in in_attrib_map.items():
            assert isinstance(in_attrib_list, (tuple, list))
            
            for in_attrib_value in in_attrib_list:
                assert isinstance(in_attrib_value, str)
                
                if not elem_in_attrib_check(elem, in_attrib_name, in_attrib_value):
                    return False
    
    if any_condition is not None:
        assert isinstance(any_condition, (tuple, list))
        
        for condition in any_condition:
            # recursion!
            if elem_condition_check(elem, condition):
                break
        else:
            return False
    
    if not_condition is not None:
        # recursion!
        if elem_condition_check(elem, not_condition):
            return False
    
    return True

# find() -- it is main function of this module
#
#   ``root_elem_list`` -- list of elems, where will be search.
#
#   ``condition_chain`` -- serial list of conditions for search
#
#   example 1:
#       import html5lib 
#       doc = html5lib.parse(text)
#       for icon_elem in find((doc,), (
#                   {'tag': '{http://www.w3.org/1999/xhtml}head'},
#                   {'tag': '{http://www.w3.org/1999/xhtml}link', 'in_attrib': {'rel': ('icon',)}},
#               )):
#           print(icon_elem.get('href'))
#
#   example 2:
#       import html5lib 
#       doc = html5lib.parse(text)
#       for icon_elem in find((doc,), (
#                   {'tag': '{http://www.w3.org/1999/xhtml}head'},
#                   {'tag': '{http://www.w3.org/1999/xhtml}meta', 'any': (
#                           {'attrib': {'name': 'description'}},
#                           {'attrib': {'name': 'keywords'}},
#                           )},
#               )):
#           print(icon_elem.get('content'))
#
def find(root_elem_list, condition_chain):
    assert isinstance(root_elem_list, (tuple, list))
    assert isinstance(condition_chain, (tuple, list))
    
    root_elem_list = tuple(root_elem_list)
    condition_chain = tuple(condition_chain)
    
    candidate_list = []
    condition = condition_chain[0]
    next_condition_chain = condition_chain[1:]
    
    for root_elem in root_elem_list:
        for elem in root_elem.iter():
            if elem in candidate_list:
                continue
            
            if elem_condition_check(elem, condition):
                candidate_list.append(elem)
    
    if candidate_list and next_condition_chain:
        # recursion!
        return find(candidate_list, next_condition_chain)
    
    return tuple(candidate_list)
