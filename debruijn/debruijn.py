#!/bin/env python3
# -*- coding: utf-8 -*-
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#    A copy of the GNU General Public License is available at
#    http://www.gnu.org/licenses/gpl-3.0.html

"""Perform assembly based on debruijn graph."""

import argparse
import os
import sys
import networkx as nx
import matplotlib
from operator import itemgetter
import random
random.seed(9001)
from random import randint
import statistics
import textwrap
import matplotlib.pyplot as plt
matplotlib.use("Agg")

__author__ = "Roude JEAN MARIE"
__copyright__ = "Universite Paris Diderot"
__credits__ = ["Roude JEAN MARIE"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = "Roude JEAN MARIE"
__email__ = "roude.etu@gmail.com"
__status__ = "Developpement"

def isfile(path): # pragma: no cover
    """Check if path is an existing file.

    :param path: (str) Path to the file
    
    :raises ArgumentTypeError: If file doesn't exist
    
    :return: (str) Path 
    """
    if not os.path.isfile(path):
        if os.path.isdir(path):
            msg = "{0} is a directory".format(path)
        else:
            msg = "{0} does not exist.".format(path)
        raise argparse.ArgumentTypeError(msg)
    return path


def get_arguments(): # pragma: no cover
    """Retrieves the arguments of the program.

    :return: An object that contains the arguments
    """
    # Parsing arguments
    parser = argparse.ArgumentParser(description=__doc__, usage=
                                     "{0} -h"
                                     .format(sys.argv[0]))
    parser.add_argument('-i', dest='fastq_file', type=isfile,
                        required=True, help="Fastq file")
    parser.add_argument('-k', dest='kmer_size', type=int,
                        default=22, help="k-mer size (default 22)")
    parser.add_argument('-o', dest='output_file', type=str,
                        default=os.curdir + os.sep + "contigs.fasta",
                        help="Output contigs in fasta file (default contigs.fasta)")
    parser.add_argument('-f', dest='graphimg_file', type=str,
                        help="Save graph as an image (png)")
    return parser.parse_args()


def read_fastq(fastq_file):
    """Extract reads from fastq files.

    :param fastq_file: (str) Path to the fastq file.
    :return: A generator object that iterate the read sequences. 
    """
    with open(fastq_file, "r") as fastq_in:
        iterator = iter(fastq_in)
        while(next(iterator, None)):
            sequence = next(fastq_in)
            yield sequence.strip()
            next(fastq_in)
            next(fastq_in)


def cut_kmer(read, kmer_size):
    """Cut read into kmers of size kmer_size.
    
    :param read: (str) Sequence of a read.
    :return: A generator object that iterate the kmers of of size kmer_size.
    """
    for i in range(len(read) - kmer_size + 1):
        yield read[i: i + kmer_size]


def build_kmer_dict(fastq_file, kmer_size):
    """Build a dictionnary object of all kmer occurrences in the fastq file

    :param fastq_file: (str) Path to the fastq file.
    :return: A dictionnary object that identify all kmer occurrences.
    """
    kmer_dict = dict()
    for sequence in read_fastq(fastq_file):
        for kmer in cut_kmer(sequence, kmer_size):
            kmer_dict[kmer] = kmer_dict.get(kmer, 0) + 1

    return kmer_dict


def build_graph(kmer_dict):
    """Build the debruijn graph

    :param kmer_dict: A dictionnary object that identify all kmer occurrences.
    :return: A directed graph (nx) of all kmer substring and weight (occurrence).
    """
    G = nx.DiGraph()
    kmer_items = list(kmer_dict.items())
    for i, (key_i, value_i) in enumerate(kmer_items):
        G.add_edge(key_i[:-1], key_i[1:], weight=value_i)

    return G


def remove_paths(graph, path_list, delete_entry_node, delete_sink_node):
    """Remove a list of path in a graph. A path is set of connected node in
    the graph

    :param graph: (nx.DiGraph) A directed graph object
    :param path_list: (list) A list of path
    :param delete_entry_node: (boolean) True->We remove the first node of a path 
    :param delete_sink_node: (boolean) True->We remove the last node of a path
    :return: (nx.DiGraph) A directed graph object
    """
    for path in path_list:
        for i in range(len(path) - 1):
            graph.remove_edge(path[i], path[i+1])

    if delete_entry_node:
        graph.remove_nodes_from([i[0] for i in path_list])
    if delete_sink_node:
        graph.remove_nodes_from([i[-1] for i in path_list])
    # Removes isolated nodes
    graph.remove_nodes_from(list(nx.isolates(graph)))

    return graph


def select_best_path(graph, path_list, path_length, weight_avg_list, 
                     delete_entry_node=False, delete_sink_node=False):
    """Select the best path between different paths

    :param graph: (nx.DiGraph) A directed graph object
    :param path_list: (list) A list of path
    :param path_length_list: (list) A list of length of each path
    :param weight_avg_list: (list) A list of average weight of each path
    :param delete_entry_node: (boolean) True->We remove the first node of a path 
    :param delete_sink_node: (boolean) True->We remove the last node of a path
    :return: (nx.DiGraph) A directed graph object
    """
    if len(path_list) == 1:
        return graph

    path_list_ = path_list
    std_weight = statistics.stdev(weight_avg_list)
    std_length = statistics.stdev(path_length)
    selected_path_index = -1
    if std_weight > 0:
        selected_path_index = weight_avg_list.index(max(weight_avg_list))
    elif std_length > 0:
        selected_path_index = path_length.index(max(path_length))
    else:
        selected_path_index = randint(0, len(path_list) - 1)

    # Keep paths to remove
    path_list_.pop(selected_path_index)
    graph = remove_paths(graph, path_list_, delete_entry_node, delete_sink_node)
    return graph
    

def path_average_weight(graph, path):
    """Compute the weight of a path

    :param graph: (nx.DiGraph) A directed graph object
    :param path: (list) A path consist of a list of nodes
    :return: (float) The average weight of a path
    """
    return statistics.mean([d["weight"] for (u, v, d) in graph.subgraph(path).edges(data=True)])


def solve_bubble(graph, ancestor_node, descendant_node):
    """Explore and solve bubble issue

    :param graph: (nx.DiGraph) A directed graph object
    :param ancestor_node: (str) An upstream node in the graph 
    :param descendant_node: (str) A downstream node in the graph
    :return: (nx.DiGraph) A directed graph object
    """
    all_paths = list(nx.all_simple_paths(graph, ancestor_node, descendant_node))
    all_weigths = [path_average_weight(graph, path) for path in all_paths]
    all_length = [len(path)-1 for path in all_paths]
    graph = select_best_path(graph, all_paths, all_length, all_weigths)
    return graph

def simplify_bubbles(graph):
    """Detect and explode bubbles

    :param graph: (nx.DiGraph) A directed graph object
    :return: (nx.DiGraph) A directed graph object
    """
    bubble = False
    noeud_descendant = None
    noeud_ancetre = None
    for node in graph:
        node_predecc = list(graph.predecessors(node))
        if len(node_predecc) > 1:
            for i, node_i in enumerate(node_predecc):
                for node_j in node_predecc[i + 1:]:
                    noeud_ancetre = nx.lowest_common_ancestor(graph, node_i, node_j)
                    if noeud_ancetre is not None:
                        noeud_descendant = node
                        bubble = True
                        break
                if bubble:
                    break
    if bubble:
        graph = simplify_bubbles(solve_bubble(graph, noeud_ancetre, noeud_descendant))

    return graph

def solve_entry_tips(graph, starting_nodes):
    """Remove entry tips

    :param graph: (nx.DiGraph) A directed graph object
    :return: (nx.DiGraph) A directed graph object
    """
    for node in graph:
        node_predecc = list(graph.predecessors(node))
        if len(node_predecc) > 1:
            paths = [list(nx.all_simple_paths(graph, node_start_i, node))\
                     for node_start_i in starting_nodes]
            paths = [path[0] for path in paths if len(path) > 0]
            lengths = [len(path) - 1 for path in paths]
            weights = [path_average_weight(graph, path) if lengths[i] > 1 else \
                       graph.get_edge_data(*path)["weight"]
                       for i, path in enumerate(paths)]

            graph = select_best_path(graph, paths, lengths, weights, 
                                     delete_entry_node=True, delete_sink_node=False)
            graph = solve_entry_tips(graph, starting_nodes)
            break

    return graph

def solve_out_tips(graph, ending_nodes):
    """Remove out tips

    :param graph: (nx.DiGraph) A directed graph object
    :return: (nx.DiGraph) A directed graph object
    """
    for node in graph:
        node_success = list(graph.successors(node))
        if len(node_success) > 1:
            paths = [list(nx.all_simple_paths(graph, node, node_end_i))\
                     for node_end_i in ending_nodes]
            paths = [path[0] for path in paths if len(path) > 0]
            lengths = [len(path) - 1 for path in paths]
            weights = [path_average_weight(graph, path) if lengths[i] > 1 else \
                       graph.get_edge_data(*path)["weight"]
                       for i, path in enumerate(paths)]

            graph = select_best_path(graph, paths, lengths, weights, 
                                     delete_entry_node=False, delete_sink_node=True)
            graph = solve_out_tips(graph, ending_nodes)
            break

    return graph

def get_starting_nodes(graph):
    """Get nodes without predecessors

    :param graph: (nx.DiGraph) A directed graph object
    :return: (list) A list of all nodes without predecessors
    """
    no_predecessors = []
    for node in graph:
        predecessors_list = list(graph.predecessors(node))
        if len(predecessors_list) == 0:
            no_predecessors.append(node)
    return no_predecessors


def get_sink_nodes(graph):
    """Get nodes without successors

    :param graph: (nx.DiGraph) A directed graph object
    :return: (list) A list of all nodes without successors
    """
    no_successors = []
    for node in graph:
        predecessors_list = list(graph.successors(node))
        if len(predecessors_list) == 0:
            no_successors.append(node)
    return no_successors

def get_contigs(graph, starting_nodes, ending_nodes):
    """Extract the contigs from the graph

    :param graph: (nx.DiGraph) A directed graph object 
    :param starting_nodes: (list) A list of nodes without predecessors
    :param ending_nodes: (list) A list of nodes without successors
    :return: (list) List of [contiguous sequence and their length]
    """
    contigs = []
    for start in starting_nodes:
        for end in ending_nodes:
            paths_gen = nx.all_simple_paths(graph, start, end)
            sequence_str = None
            for path in paths_gen:
                sequence_str = path[0]
                for j in path[1:]:
                    sequence_str += j[len(path[0]) - 1:]
                contigs.append((sequence_str, len(sequence_str)))

    return contigs


def save_contigs(contigs_list, output_file):
    """Write all contigs in fasta format

    :param contig_list: (list) List of [contiguous sequence and their length]
    :param output_file: (str) Path to the output file
    """
    with open(output_file, "w") as fasta_out:
        to_write = ""
        for i, (contig, length) in enumerate(contigs_list):
            to_write += f">contig_{i} len={length}\n"
            to_write += textwrap.fill(contig, width=80)
            if i != len(contig) - 1:
                to_write += "\n"
        fasta_out.write(to_write)


def draw_graph(graph, graphimg_file): # pragma: no cover
    """Draw the graph

    :param graph: (nx.DiGraph) A directed graph object
    :param graphimg_file: (str) Path to the output file
    """                                   
    fig, ax = plt.subplots()
    elarge = [(u, v) for (u, v, d) in graph.edges(data=True) if d['weight'] > 3]
    #print(elarge)
    esmall = [(u, v) for (u, v, d) in graph.edges(data=True) if d['weight'] <= 3]
    #print(elarge)
    # Draw the graph with networkx
    #pos=nx.spring_layout(graph)
    pos = nx.random_layout(graph)
    nx.draw_networkx_nodes(graph, pos, node_size=6)
    nx.draw_networkx_edges(graph, pos, edgelist=elarge, width=6)
    nx.draw_networkx_edges(graph, pos, edgelist=esmall, width=6, alpha=0.5, 
                           edge_color='b', style='dashed')
    #nx.draw_networkx(graph, pos, node_size=10, with_labels=False)
    # save image
    plt.savefig(graphimg_file)


#==============================================================
# Main program
#==============================================================
def main(): # pragma: no cover
    """
    Main program function
    """
    # Get arguments
    args = get_arguments()
    kmer_dict = build_kmer_dict(args.fastq_file, args.kmer_size)
    graph = build_graph(kmer_dict)
    graph = simplify_bubbles(graph)
    graph = solve_entry_tips(graph, get_starting_nodes(graph))
    graph = solve_out_tips(graph, get_sink_nodes(graph))
    contigs = get_contigs(graph, get_starting_nodes(graph), get_sink_nodes(graph))
    save_contigs(contigs, args.output_file)
    # Fonctions de dessin du graphe
    # A decommenter si vous souhaitez visualiser un petit 
    # graphe
    # Plot the graph
    if args.graphimg_file:
        draw_graph(graph, args.graphimg_file)
    
if __name__ == '__main__': # pragma: no cover
    main()
