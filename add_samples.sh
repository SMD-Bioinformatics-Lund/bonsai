# add species
curl                                               \
	-X POST                                        \
	http://mtlucmds2.lund.skane.se:8011/groups/   \
	-H 'Content-Type: application/json'            \
	-d '{"group_id": "saureus", "display_name": "Staphylococcus aureus", "included_samples": [], "table_columns": [ { "hidden": false, "type": "sample_id", "name": "sample_id", "label": "Sample ID", "sortable": true, "filterable": false }, { "hidden": false, "type": "text", "name": "specie", "label": "Species", "sortable": true, "filterable": true, "filter_type": "selection", "filter_param": "includes" }]}'
#curl                                               \
#	-X POST                                        \
#	http://mtlucmds2.lund.skane.se:8011/groups/saureus/image   \
#	-F image=@/trannel/proj/cgviz/client/src/images/staphylococcus_aureus.jpg
echo 
echo "================="
echo "==  Get groups  ="
echo "================="
curl http://mtlucmds2.lund.skane.se:8011/groups/
echo 
echo "=============================="
echo "==  Get specific collection  ="
echo "=============================="
curl http://mtlucmds2.lund.skane.se:8011/groups/saureus
echo 
echo "=================="
echo "==  Post sample  ="
echo "=================="
echo 
#-d "{'group_id': 'foo-bar', 'sample': ${test_sample}}"
test_sample=$(cat test_sample.json)
curl                                               \
	-X POST                                        \
	http://mtlucmds2.lund.skane.se:8011/samples/   \
	-H 'Content-Type: application/json'            \
	-d "${test_sample}"
echo 
echo "=================="
echo "==  GET  sample  ="
echo "=================="
echo 
curl http://mtlucmds2.lund.skane.se:8011/samples/some-sample-id

echo 
echo "============================"
echo "==  Add comment to sample =="
echo "============================"
echo 
curl                                               \
	-X POST                                        \
	'http://mtlucmds2.lund.skane.se:8011/samples/some-sample-id/comment' \
	-H 'Content-Type: application/json'            \
	-d '{"username": "foo-bar", "comment": "foo bar doo"}'

echo 
echo "=========================="
echo "==  Add sample to group  ="
echo "=========================="
echo 
curl                                               \
	-X PUT                                         \
	-G                                             \
	--data-urlencode 'sample_id=some-sample-id'    \
	'http://mtlucmds2.lund.skane.se:8011/groups/saureus/sample'
echo 
#echo "==============="
#echo "==  Add user  ="
#echo "==============="
#echo 
#curl                                               \
#	-X POST                                        \
#	'http://mtlucmds2.lund.skane.se:8011/users/' \
#	-H 'Content-Type: application/json'            \
#	-d '{"username": "foo-bar", "first_name": "foo", "last_name": "bar", "email": "foo.bar@skane.se", "password": "abc"}'
#echo 
#echo "==============="
#echo "==  Get user  ="
#echo "==============="
#echo 
#curl 'http://mtlucmds2.lund.skane.se:8011/users/foo-bar'
#echo 
#echo "==================="
#echo "==  Add location  ="
#echo "==================="
#echo 
#curl                                               \
#	-X POST                                        \
#	'http://mtlucmds2.lund.skane.se:8011/locations/' \
#	-H 'Content-Type: application/json'            \
#	-d '{"display_name": "Peppes bodega", "coordinates": [55.54022974807241, 13.956022281761875]}'
#curl                                               \
#	-X POST                                        \
#	'http://mtlucmds2.lund.skane.se:8011/locations/' \
#	-H 'Content-Type: application/json'            \
#	-d '{"display_name": "Lelles ved och porr", "coordinates": [55.544019997791, 13.944303582525]}'
#echo
#echo "==  Get locations  ="
#curl 'http://mtlucmds2.lund.skane.se:8011/locations/'
#echo
#echo "==  Get location  ="
#curl 'http://mtlucmds2.lund.skane.se:8011/locations/622b33bf48b741fb7374b12d'
#echo
#echo "==  Get location within bbox  ="
#curl -G 'http://mtlucmds2.lund.skane.se:8011/locations/bbox' \
#	--data-urlencode "left=55.5397226" \
#	--data-urlencode "right=55.5406246" \
#	--data-urlencode "top=13.9579821" \
#	--data-urlencode "bottom=13.9556113"
#echo
#echo "==  Add location to sample  ="
#curl                                               \
#	-X PUT                                         \
#	'http://mtlucmds2.lund.skane.se:8011/samples/some-sample-id/location' \
#	-H 'Content-Type: application/json'            \
#	-d '"622b56ee853513156095f5dc"'
