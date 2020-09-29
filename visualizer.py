#!/usr/bin/python3

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# See the LICENSE file for more details.

import re
import os
from graphviz import Digraph
import random
import argparse

def collect_label_translation(aux_file):
    label_trans = {}
    with open(aux_file) as f: 
        for line in f:
            m = re.match('\\\\newlabel\{([a-zA-Z:0-9=]+)\}', line)
            if m is None:
                continue
            label = m.group(1)
            trans = line.split('}{')[-2]
            label_trans[label] = trans
    return label_trans

def possible_translation(tex_file, theorem_list):
    aux_file = tex_file.replace('tex', 'aux')
    if not os.path.exists(aux_file):
        return
    label_trans = collect_label_translation(aux_file)
    for item in theorem_list:
        label = item['latex_label']
        if label == '':
            continue
        item['latex_label'] = label_trans[label]
        item['references'] = [label_trans[i] for i in item['references']]

def collect_theorems(input_file, hierarchy, theorem_names, outmost_counter_init):
    hierarchy_counter = {}
    for h in hierarchy:
        hierarchy_counter[h] = 0

    if hierarchy:
        hierarchy_counter[hierarchy[0]] = outmost_counter_init - 1

    inner_counter = 0

    theorems = []

    looking_for_label = False
    looking_for_references = False


    with open(input_file) as f: 
        for line in f:
            # respect comments
            line = line.split('%')[0]

            # update the hierarchy counters
            for (h,i) in zip(hierarchy,range(len(hierarchy))):
                r = r'.*\\' + re.escape(h)
                if re.match(r, line):
                    hierarchy_counter[h] += 1
                    inner_counter = 0
                    for h_ in [h__ for h__ in hierarchy][(i+1):]:
                        hierarchy_counter[h_] = 0

            # look for theorems 
            for t in theorem_names:
                r = r'.*\\begin\{' + re.escape(t) + r'\}'
                if re.match(r,line):
                    inner_counter += 1
                    number_string = '.'.join([str(hierarchy_counter[h]) for h in hierarchy_counter] + [str(inner_counter)])
                    theorems.append({'number': number_string, 'latex_label':'', 'references':[], 'used':False, 'show_label': True})
                    looking_for_label = True
                    looking_for_references = True

                r = r'.*\\end\{' + re.escape(t) + r'\}'
                if re.match(r,line):
                    looking_for_label = False
            
            # look for labels
            if looking_for_label:
                r = r'.*\\label\{(.*?)\}'
                m = re.match(r, line)
                if m:
                    theorems[-1]['latex_label'] = m.group(1)
                    looking_for_label = False

            # look for references
            if looking_for_references:
                r = r'\\ref\{(.*?)\}'
                matches = re.findall(r, line)
                for m in matches:
                    theorems[-1]['references'].append(m)

            # stop looking for references at end of proof environment
            r = r'.*\\end\{proof\}' 
            if re.match(r, line):
                looking_for_references = False

            # likewise stop looking for references at \qed
            r = r'.*\\qed' 
            if re.match(r, line):
                looking_for_references = False

    return theorems

def build_graph(theorems, option_show_label, option_existing_theorems_only):
    # generate labels if the theorem has no label in latex
    for t in theorems:
        if not t['latex_label']:
            t['latex_label'] = t['number'] + '_' + str(hash(t['number']))
            t['show_label'] = False

    G = Digraph(comment='dependency graph', strict=True)

    def mark_used(latex_label):
        for t in theorems:
            if t['latex_label'] == latex_label:
                t['used'] = True
                break

    def node_exists(latex_label):
        for t in theorems:
            if t['latex_label'] == latex_label:
                return True
        return False

    for t in theorems:
        for r in t['references']:
            if (not option_existing_theorems_only) or node_exists(r):
                mark_used(r)
                t['used'] = True
                G.edge(r, t['latex_label'])

    for t in theorems:
        if t['used']:
            label_text = ' = ' + t['latex_label'] if (t['show_label'] and option_show_label) else ''
            G.node(t['latex_label'],t['number'] + label_text)

    return G

def main():

    # -----------------------------
    # Parse command line arguments

    parser = argparse.ArgumentParser(description='Visualize theorem dependencies in latex documents.')
    parser.add_argument('-i','--input', help='the latex file you want to use.', required=True)
    parser.add_argument('-c','--config', help='the config file, leave empty to use default config', required=False, default='config')
    parser.add_argument('-o','--output', help='the name of the output file', required=False, default='out.gv')
    parser.add_argument('-f','--first_chapter', help='number of the first chapter, defaults to 1', required=False, type=int, default=1)
    parser.add_argument('-n','--no_labels', help='hide labels', action='store_false')
    parser.add_argument('-a','--all_theorems', help='show references that were not found in the file', action='store_false')
    args = vars(parser.parse_args())

    # convenience
    config_file = args['config']
    input_file = args['input']
    output_file = args['output']
    outmost_counter_init = args['first_chapter']
    option_show_label = args['no_labels']
    option_existing_theorems_only = args['all_theorems']

    # -----------------------------
    # Parse config file

    hierarchy = []
    theorem_names = []

    with open(config_file) as f: 
        for line in f:
            line = line.strip()
            line = line.split(' ')
            if line[0] == 'theorem_names:':
                theorem_names = line[1:]
            elif line[0] == 'hierarchy:':
                hierarchy = line[1:]

    # -----------------------------
    # build graph

    theorems = collect_theorems(input_file, hierarchy, theorem_names, outmost_counter_init)
    possible_translation(input_file, theorems)
    G = build_graph(theorems, option_show_label, option_existing_theorems_only)

    # -----------------------------
    # output the graph as png and open with default application

    G.render(view=True,format='png',filename=output_file)


if __name__== "__main__":
    main()