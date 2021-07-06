from Bio.Phylo.TreeConstruction import DistanceCalculator, DistanceMatrix, DistanceTreeConstructor
from Bio import Phylo
from Bio import AlignIO



def neighbor_joining(data):

    dm = DistanceMatrix(names=data["names"], matrix=data["matrix"])

    constructor = DistanceTreeConstructor()
    tree = constructor.nj(dm)

    #print dm
    return tree
