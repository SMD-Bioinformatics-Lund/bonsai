var help_text = {};
help_text["load_files"] =
  "<p align='center'><h2>\
<b>G</b>rape <b>T</b>ree\
</h2>\
</p>\
To get started Drag and drop files into the browser window\
<h4>Trees or Profile Data</h4>\
<ul>\
<li><b>Phylogenetic trees</b> These can be nexus or nwk format. \
</li>\
<li>\
<b>Profile Files</b> These are tab delimited text with columns as alleles and strains as rows (see the examples). \
A header line is required, in which columns for strain names, ST ids and metadata need to start with a '#'. Any column that is not start with a '#' will be recognised as alleles. \
This requires the local server to be running. \
</li>\
<li><b>Custom Format(.json)</b> Files generated by this program which contain the tree data exactly as displayed and any metadata.\
</li>\
</ul>\
<h4>Metadata</h4>\
<ul>\
<li>\
<b>Metadata files</b> The first column in the file corresponds to the node identifier in the tree. \
</li>\
</ul>";
help_text["save_grapetree"] =
  '<h2><a id="Saving_in_GrapeTree_13"></a>Saving in GrapeTree</h2>\
<ul>\
<li><strong>Save GrapeTree</strong>: Save the tree to a JSON format file, which contains the tree data exactly as displayed and any metadata. Only compatible with GrapeTree.</li>\
<li><strong>Save as Newick Tree</strong>: Save the tree as a <a href="https://en.wikipedia.org/wiki/Newick_format">Newick (nwk)</a> file, which contains tree topology, branch lengths and tip names. Compatible with most tree visualisation tools.</li>\
<li><strong>Download SVG</strong>: Save the tree as a <a href="https://en.wikipedia.org/wiki/Scalable_Vector_Graphics">Scalar Vector Graphic (SVG)</a> file, a vector image that can be loaded into image publishing software such as Inkscape or Abobe llustrator.</li>\
</ul>';
help_text["tree_layout"] =
  '<h2><a id="Modifying_the_Tree_Layout_18"></a>Modifying the Tree Layout</h2>\
<ul>\
<li><strong>Original Tree</strong>: Reverts the tree to the original state when it was loaded. You will lose all your changes!</li>\
<li><strong>Static redraw</strong>: Redraws the tree using the static layout. You will lose any manual adjustments to node positioning!</li>\
<li><strong>Centre Tree</strong>: Adjusts view settings to place entire tree in the centre of the window.</li>\
<li><strong>Show Tooltips</strong>: Shows tooltips for branches and nodes.</li>\
<li><strong>Drag Icon to Rotate</strong>: Rotate the whole tree by dragging the icon around its original location.</li>\
<li><strong>Zoom</strong>: Enlarge or reduce the size of the tree. </li>\
</ul>';
help_text["show_labels"] =
  '<h2><a id="Customising_node_labels_24"></a>Customising node labels</h2>\
<ul>\
<li><strong>Show Labels</strong>: Check to show node labels</li>\
<li><strong>Font Size</strong>: Choose font size of node labels. Use the slider to change the value, or enter a specific value into the box</li>\
</ul>';
help_text["node_size"] =
  '<h2><a id="Customising_node_size_29"></a>Customising node size</h2>\
<ul>\
<li><strong>Node Size</strong>: Increase/Decrease size of all nodes. Click rewind icon to revert to default value. Use the slider to change the value, or enter a specific value into the box</li>\
<li><strong>Kurtosis</strong>: Increase/Decrease kurtosis of all nodes. Nodes with large number of members will look more distinct. Click rewind icon to revert to default value. Use the slider to change the value, or enter a specific value into the box. By default the area of the nodes correlate with the numbers of members in them. </li>\
<li><strong>Highlight Label</strong>: An easy way to find nodes associate with particular metdata in their displayed labels. Support regular expression. </li>\
<li><strong>Show Pie Chart</strong>: Shows breakdown of members contained within a node, categorized on "Colour by" setting</li>\
</ul>';
help_text["branch_labels"] =
  '<h2><a id="Modifying_Branch_length_and_Collapsing_branches_34"></a>Modifying Branch length and Collapsing branches</h2>\
<ul>\
<li><strong>Show Labels</strong>: Check to show node labels</li>\
<li><strong>Font Size</strong>: Choose font size of node labels. Use the slider to change the value, or enter a specific value into the box.</li>\
<li><strong>Scaling</strong>: Increase/Decrease length of all branches. Click rewind icon to revert to default value. Use the slider to change the value, or enter a specific value into the box.</li>\
<li><strong>Collapse Branches</strong>: All branches shorter than specified length will be collapses and nodes will merged together. Branch length value is scaled to the branch lengths defined in the original tree data. Use the slider to change the value, or enter a specific value into the box.</li>\
<li><strong>Log Scale</strong>: All length of all branches will be scaled logarithmically.</li>\
</ul>';
help_text["branch_cutoffs"] =
  '<h2><a id="Setting_branch_cutoffs_41"></a>Setting branch cutoffs</h2>\
<p>Branches that are over the specified length can be rendered in a particular way based on settings in this panel. Branch length value is scaled to the branch lengths defined in the original tree data. Enter a specific value into the box or use the arrows.</p>\
<ul>\
<li><strong>Display</strong>: Long Branches will be show as normal</li>\
<li><strong>Hide</strong>: Long branches will be transparent. They are interactive, but will not be shown on the tree.</li>\
<li><strong>Shorten</strong>: Long branches will be cropped back to the specified branch length cutoff. Lines will be dashed to indicate affected branches.</li>\
</ul>';
help_text["rendering"] =
  '<h2><a id="Layout_rendering_options_47"></a>Layout rendering options</h2>\
<p>Layout Rendering gives options on how nodes are positioned on the tree</p>\
<ul>\
<li><strong>Static</strong>: Tree layout is calculated when the tree is initially created and remains static. Relative branch length scaling (as specified in the original tree data)  will be maintained if "Real Branch Length" option is checked.</li>\
<li><strong>Dynamic</strong>: Nodes are positioned dynamically similar to a <a href="https://bl.ocks.org/mbostock/4062045">Force Directed Layout</a>. Nodes will try to fan out and distance themselves from neighbours. This may improve the aesthetic of the tree but will modify branch length scaling. Branch lengths are NOT to scale when this is used. The dynamic positioning can applied only to selected nodes if the "Selected Only" option is checked.</li>\
</ul>';
help_text["context_menu"] =
  '<h2><a id="Context_menu_52"></a>Context menu</h2>\
<p>Provides quick links to contextual menus, which are usually accessed by right click; this is for devices that do not have an easy right-click option such as tablets and mobile devices.</p>\
<ul>\
<li><strong>GrapeTree</strong>: Presents the same menu as when right-clicking on the tree itself.</li>\
<li><strong>Metadata</strong>: Presents the same menu as when right-clicking on the metadata table.</li>\
<li><strong>Figure Legend</strong>: Presents the same menu as when right-clicking on the Legend.</li>\
</ul>';
help_text["metadata_menu"] =
  '<h2><a id="Metadata_window_0"></a>Metadata window</h2>\
<p>Provides a table that showing loaded metadata.</p>\
<ul>\
<li><strong>Download</strong>: Export the metadata as a tab delimited file.</li>\
<li><strong>Add Metadata</strong>: Click this to add a new column, specify the field name in the column.</li>\
<li><strong>Filter</strong>: Shows filtering text boxes below each column header, when checked.</li>\
<li><strong>Hypo Nodes?</strong>: Shows hypothetical nodes in the metadata table, when checked.</li>\
</ul>';

help_text["enterobase"] =
  '<h2><a id="Saving_in_GrapeTree_13"></a>Interaction With Enterobase</h2>\
<ul>\
<li><strong>Load Selected</strong>: Any strains selected in the tree will be loaded into the main search page of Enterobase. If The main search page is not open, then a new page will open in the browser.</li>\
<li><strong>Highlight Checked</strong>: Any strains checked (selected) in the Enterobase main search page will become highlighted (large yellow halo) in the tree.</li>\
<li><strong>Import Fields</strong>: Shows a dialog box which allows the selection of experimental fields and custom fields (columns) to be imported into the tree.</li>\
<li><strong>Save</strong>:Saves the tree layout and any metadata in the tree. Changed metadata is only  associated with tree and will not be updated in Enterobase. Data in custom columns, however, which you have permission to edit, will be updated in Enterobase and you will be notified if this is the case.</li>\
<li><strong>Update</strong>: Will update the tree with any metadata that has changed  in Enterobase since the tree was created or the last update.  Also any data from custom columns, which has changed in Enterobase will also be updated in ther tree.</li>\
<li><strong>Info</strong>: Shows information about the tree such as the parameters used for construction, number of strains, last modified etc. </li>\
</ul>';

for (var k in help_text) {
  help_text[k] = [
    help_text[k],
    '<br><br>The complete documentation can be found in <a href="http://enterobase.readthedocs.io/en/latest/grapetree/grapetree-about.html" target="_blank">Online Documents</a>',
  ];
}
