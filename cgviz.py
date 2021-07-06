import os
import sys
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, jsonify
from flask_pymongo import PyMongo
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
#from flask_table import 
from bson.objectid import ObjectId
from datetime import datetime, timedelta
import arrow
import dateutil
import pprint
import json
import re
import phylogeny
from user import User
from forms import LoginForm
from collections import defaultdict
import time

app = Flask(__name__)
mongo = PyMongo(app)
login_manager = LoginManager()
login_manager.init_app(app)
app.config.from_object('config')

login_manager.login_view = "login"


@app.route('/')
@login_required
def species_select():

    # Get groups of user
    user_role = current_user.get_role()

    query = {}
    if user_role != "admin":
        pass
        #query = {'species': {'$ne': 'test'}}
    
    species = app.config['SPECIES_COLL'].find( query )
    counts  = app.config['SAMPLES_COLL'].aggregate( [ {'$group': {'_id':"$species", 'count':{'$sum':1}}} ] )
    counts_dict = {}
    for c in counts:
        counts_dict[c["_id"]] = c["count"]
    
    return render_template( 'index.html', species=species, counts=counts_dict )


@app.route('/<string:spec>')
@login_required
def main_screen(spec):

    # Get groups of user
    user_role = current_user.get_role()

    samples = app.config['SAMPLES_COLL'].find( { 'species':spec }, { 'alleles':0 } ).sort('_id', -1 )
    species = app.config['SPECIES_COLL'].find_one( { 'species':spec } )

    return render_template( 'main.html', samples=samples, species=species, user_role=user_role )




@app.route('/_showdata')
@login_required
def show_sample_data():
    sample_id = request.args.get("sample")

    data = app.config['SAMPLES_COLL'].find_one( { '_id': ObjectId(sample_id) } )
    data['_id'] = str(data['_id'])
    species = app.config['SPECIES_COLL'].find_one( { 'species':data["species"] }, {'_id':0} )
    
    return jsonify(sample_id=sample_id, data=data, species=species)




@app.route('/_changehidestate')
@login_required
def change_hide_state():
    species = request.args.get("species")
    name = request.args.get("name")
    checked = request.args.get("chk")

    hidden = (0 if checked=='true' else 1)
    
    result = app.config['SPECIES_COLL'].update_one( { 'species':species, 'fields': {'$elemMatch': { 'name': name } }}, {'$set': {'fields.$.hidden': hidden}} )
    
    return "OK"




@app.route('/_deletemetafield')
@login_required
def delete_meta_field():
    species = request.args.get("species")
    field   = request.args.get("field")
    result = app.config['SPECIES_COLL'].update_one( { 'species':species }, {'$pull': { 'fields': {'name':  field}}} )
    return "OK"




@app.route('/_newmetafield')
@login_required
def new_meta_field():
    species    = request.args.get("species")
    name       = request.args.get("name")
    field_type = request.args.get("type")
    visible    = request.args.get("visible")

    hidden = (0 if visible=='true' else 1)
    result = app.config['SPECIES_COLL'].update_one( { 'species':species }, {'$push': { 'fields': {'name':  name, 'label': name, 'type': field_type, 'hidden': hidden}}} )
    
    return "OK"



@app.route('/_savemetafield')
@login_required
def save_meta_field_data():
    name = request.args.get("name")
    val  = request.args.get("value")
    field, oid = name.split('|')
    result = app.config['SAMPLES_COLL'].update_one( { '_id':ObjectId(oid) }, {'$set': {'metadata.'+field: val}}, upsert=True )
    return "OK"


@app.route('/_savemetafieldmany')
@login_required
def save_meta_field_data_many():
    field = request.args.get("field")
    val  = request.args.get("value")
    sids = request.args.getlist('sids[]')
    f = open("/data/tmp/many_metadata.test","w")
    for oid in sids:
        #f.write(oid+' '+field.encode('utf-8')+' '+val.encode('utf-8')+"\n")
        result = app.config['SAMPLES_COLL'].update_one( { '_id':ObjectId(oid) }, {'$set': {'metadata.'+field: val}}, upsert=True )
    f.close()
    return "OK"




@app.route('/_savegrapetreemetadata', methods=['POST'])
@login_required
def save_grapetree_metadata():
    #data = request.form
    data = request.get_json()

    f = open("/data/tmp/grapetree_metadata.test","w")
    #f.write(pprint.pformat(data)+"\n")
    for d in data:
        oid = "null"
        save_data = {}
        for key in d.keys():
            if key in ['run', 'mlst', 'PVL', 'ID', '__selected', 'id']:
                continue

            if key=='_id':
                oid = d[key]
            else:
                if isinstance(d[key], basestring):
                    save_data['metadata.'+key.encode('utf-8')] = d[key].encode('utf-8')
                else:
                    save_data['metadata.'+key.encode('utf-8')] = d[key]
                
        f.write(oid + "\n")
        f.write(str(save_data) + "\n")
        if oid != "null":
            result = app.config['SAMPLES_COLL'].update_one( { '_id':ObjectId(oid) }, {'$set': save_data}, upsert=True )
    f.close()
    
    results = {'status':'success'} 
    return jsonify( results )


@app.route('/_hideisolate')
@login_required
def hide_isolate():
    oid = request.args.get("id")
    user_role = current_user.get_role()
    
    if user_role == 'admin' and oid:
        results = app.config['SAMPLES_COLL'].update_one( { '_id':ObjectId(oid) }, {'$set': {'hidden':True}} )
        out = {'status':'success'}
    else:
        out = {'status':'denied'}

    return jsonify(out)


@app.route('/_deleteisolate')
@login_required
def delete_isolate():
    oid = request.args.get("id")
    user_role = current_user.get_role()
    
    if user_role == 'admin' and oid:
        results = app.config['SAMPLES_COLL'].delete_one( { '_id':ObjectId(oid) } )
        out = {'status':'success'}
    else:
        out = {'status':'denied'}

    return jsonify(out)


        
@app.route('/_calcpairdist')
@login_required
def calc_pair_dist():
    sid1 = request.args.get('iso1')
    sid2 = request.args.get('iso2')
    spec = request.args.get('species')

    sample1 = app.config['SAMPLES_COLL'].find_one( { '_id': ObjectId(sid1) }, { 'alleles': 1} )
    sample2 = app.config['SAMPLES_COLL'].find_one( { '_id': ObjectId(sid2) }, { 'alleles': 1} )

    diffs = sum(i != j and i != '-' and j != '-' for i, j in zip(sample1['alleles'], sample2['alleles']))
    results = {'status':'success', 'value':diffs}
    
    return jsonify( results )


@app.route('/locimatrix')
@login_required
def loci_matrix():
    samples = list( app.config['SAMPLES_COLL'].find( { 'species': 'saureus'} ) )
    all_profiles = []
    missing = {}
    sample_missing = {}
    num_loci = len(samples[0]["alleles"])
    for s in samples:
        all_profiles.append(s["alleles"])
        for i in range(len(s["alleles"])):
            if s["alleles"][i] == '-':
                missing[i] = 1
                if s['id'] in sample_missing:
                    sample_missing[s['id']] += 1
                else:
                    sample_missing[s['id']] = 1

    missing_cnt = 0
    for i in range(num_loci):
        if i in missing and missing[i] == 1:
            missing_cnt += 1

    return render_template( 'loci_matrix.html', profiles=all_profiles, missing=missing, num_loci=num_loci, missing_cnt=missing_cnt, sample_missing=sample_missing )
                                                                                                                                                                                        
    
@app.route('/_maketree', methods=['GET', 'POST'])
@login_required
def generate_tree():
    
    #sample_id_strs = request.args.getlist('samples[]')
    #spec = request.args.get('species')
    #mlst = request.args.get('mlst')
    
    sample_id_strs = request.form.getlist('samples[]')
    spec = request.form.get('species')
    mlst = request.form.get('mlst')
    
    os.remove("/data/tmp/pyout")
    
    f = open("/data/tmp/pyout", "w")
    sample_ids = []
    for sid_str in sample_id_strs:
        f.write(sid_str+"\n")
        sample_ids.append(ObjectId(sid_str))
    f.close()

    # Get a list of metadata fields for the species
    metadata_fields = []
    species = app.config['SPECIES_COLL'].find_one( { 'species':spec } )

    #    for s in species:
    for metafield in species['fields']:
        if metafield.get("hidden", 0) == 0:
            metadata_fields.append(metafield["name"])

    
    samples = list( app.config['SAMPLES_COLL'].find( { '_id': { '$in': sample_ids } } ) )
    diffs = []

    sample_names = [ x["id"] for x in samples ]


    tt = open("/data/tmp/testtest", "w")    
    # Check that all samples use the same scheme!
    prev_md5 = ""
    for s in samples:
        tt.write(pprint.pformat(s))

        if "scheme_md5" not in s or ( prev_md5 != "" and s["scheme_md5"] != prev_md5 ):
            return "ERROR" # FIXME: Generate proper error message!
        prev_md5 = s["scheme_md5"]

    tt.close()    
    

    # Get scheme from database
    scheme = app.config['SCHEMES_COLL'].find_one( { 'md5': prev_md5 } )
        
    os.remove("/data/tmp/cgprof.tmp")
    # Write profile to a temporary file to be sent to GrapeTree
    profile_file = open("/data/tmp/cgprof.tmp", "w")
    metadata = {}
    if mlst == "1":
        profile_file.write( "#Name\tST\t" + "1\t2\t3\t4\t5\t6\t7\n" )
    else:
        profile_file.write( "#Name\tST\t" + "\t".join(scheme["loci"]) + "\n" )

    for s in samples:
        if mlst == "1":
            alleles = []
            for key in sorted(s["mlst"]["alleles"].keys()):
                alleles.append(s["mlst"]["alleles"][key]) 
            profile_file.write( s["id"] + "\t1"+ "\t" + "\t".join(alleles) + "\n" )
        else:
            profile_file.write( s["id"] + "\t1"+ "\t" + "\t".join(s["alleles"]) + "\n" )

        metadata[s["id"]] = {}
        for mf in metadata_fields:
            if s["metadata"] is not None and mf in s["metadata"]:
                metadata[s["id"]][mf] = s["metadata"][mf]
            else:
                metadata[s["id"]][mf] = ""

        if "mlst" in s:
            metadata[s['id']]['mlst'] = s["mlst"]["sequence_type"]

        if "run" in s:
            metadata[s['id']]['run'] = s["run"].split('/')[-1]

        metadata[s['id']]['PVL'] = format_virulence(s, "PVL")
        metadata[s['id']]['_id'] = str(s["_id"])

        
    profile_file.close()

    
    # Initialize difference matrix
    #matrix = [[-1 for x in range(1+len(samples))] for y in range(len(samples))] 
    #for i1, samp1 in enumerate(samples):
    #    row = []
    #    matrix[i1][0] = sample_names[i1]
    #    for i2, samp2 in enumerate(samples):
    #        if i1 >= i2:
    #            diffs = [ i for i, j in zip(samp1["alleles"],samp2["alleles"]) if i != j and i != "-" and j != "-" ]
    #            row.append(len(diffs));
    #            matrix[i1][i2+1] = len(diffs)
            
    return jsonify(metadata=metadata )




def redirect_url(default='index'):
    return request.args.get('next') or request.referrer or url_for(default)

@app.template_filter()
def metadata(data, val):
    if data is not None and "metadata" in data and data["metadata"] is not None:
        s = data["metadata"].get(val, "-")
        if len(s) > 0:
            return s

    return "-"


@app.template_filter()
def format_virulence(data, which):
    if data is None or "aribavir" not in data:
        return "NA"

    vir = data.get("aribavir", {})
    
    if which == "PVL":
        if vir and vir.get("lukS_PV") and vir.get("lukF_PV"):
            lukS = vir.get("lukS_PV").get("present", 0)
            lukF = vir.get("lukF_PV").get("present", 0)
            if lukS == 1 and lukF == 1:
                return "pos"
            elif lukS == 1:
                return "neg/pos"
            elif lukF == 1:
                return "pos/neg"
            else:
                return "neg"
        else:
            return "NA"

    else:
        return "???"
        

@app.template_filter()
def human_date(value):
    time_zone = "CET"
    return (arrow.get(value)
        .replace(tzinfo=dateutil.tz.gettz(time_zone))
        .humanize())


@app.template_filter()
def oid2date(id):
    return id.generation_time

@app.template_filter()
def full_date(value):
    if( value ):
        return value.strftime('%Y-%m-%d, %H:%M:%S')
    else:
        return "N/A"

    
@login_manager.user_loader
def load_user(username):
    u = app.config['USERS_COLL'].find_one({"_id": username})
    if not u:
        return None
    return User(u['_id'], u['groups'], u.get('cgviz_role', 'normal'))


@app.route('/login', methods=['GET', 'POST'])
def login():  
    form = LoginForm()
    if request.method == 'POST' and form.validate_on_submit():
        user = app.config['USERS_COLL'].find_one({"_id": form.username.data})
        if user and User.validate_login(user['password'], form.password.data):
            user_obj = User(user['_id'], user['groups'], user.get('cgviz_role','normal'))
            login_user(user_obj)

            return redirect(request.args.get("next") or url_for("species_select"))

    return render_template('login.html', title='login', form=form)


@app.route('/logout')
def logout():  
    logout_user()
    return redirect(url_for('login'))

@app.route('/diff')
@login_required
def calc_diff():
    samples = list( app.config['SAMPLES_COLL'].find( { 'spa':1, 'species':'SAu' }, { 'name':1, 'cg_mlst':1 } ) )

    before = time.time()
    diff_str = ""
    for i1, samp1 in enumerate(samples):
        for i2, samp2 in enumerate(samples):
            if i1 < i2:
                continue
            diffs = [ i for i, j in zip(samp1["cg_mlst"],samp2["cg_mlst"]) if i != j]
    return "DONE: " + str(time.time()-before)
    return render_template('diff.html', diff_str = diff_str)


if __name__ == "__main__":
    app.run()


    
