#!/usr/bin/python3
# context/__init__.py
# under construction
# utilities for extracting state context info and inserting it into the files in the context folder
import sys
import re
from munge_routines import id_from_select_or_insert, format_type_for_insert, composing_from_reporting_unit_name, format_type_for_insert_PANDAS
import db_routines as dbr
import pandas as pd

def context_to_cdf(session,meta,s,schema,cdf_def_dirpath = 'CDF_schema_def_info/'):
    """Takes the info from the context_dictionary for the state s and inserts it into the db.
    Returns a dictionary mapping context_dictionary keys to the database keys """ # TODO is the dictionary necessary?
    out_d = {}
    if not cdf_def_dirpath[-1] == '/': cdf_def_dirpath += '/'
    with open(cdf_def_dirpath+'tables.txt','r') as f:
        table_def_list = eval(f.read())

    for table_def in table_def_list:      # iterating over tables in the common data format schema
        t = table_def[0]      # e.g., cdf_table = 'ReportingUnit'
        out_d[t] = {}

        ## load info into the tables corresponding directly to the context_dictionary keys
        if t in s.context_dictionary.keys():
            print('\tProcessing ' + t + 's')


            if t == 'BallotMeasureSelection':   # note: s.context_dictionary['BallotMeasureSelection'] is a set not a dict
                for bms in s.context_dictionary['BallotMeasureSelection']:
                    value_d = {'Selection': bms}
                    id_from_select_or_insert(session,meta.tables[schema + '.' + t],  value_d)
            else:
                nk_list =  list(s.context_dictionary[t])
                for name_key in nk_list:   # e.g., name_key = 'North Carolina;Alamance County'
                    # track progress
                    if nk_list.index(name_key) % 500 == 0:   # for every five-hundredth item
                        print('\t\tProcessing item number '+str(nk_list.index(name_key))+': '+ name_key)
                    ## insert the record into the db
                    value_d = {'Name':name_key}
                    for f in table_def[1]['fields']:
                        if f['fieldname'] in s.context_dictionary[t][name_key].keys():
                            value_d[f['fieldname']] = s.context_dictionary[t][name_key][ f['fieldname'] ]
                    for e in table_def[1]['enumerations']:
                        if e in s.context_dictionary[t][name_key].keys():
                            [id,other_txt] = format_type_for_insert(session,meta.tables[schema + '.' + e],s.context_dictionary[t][name_key][e])
                            value_d[e+'_Id'] = id
                            value_d['Other'+e] = other_txt
                    ru_id = id_from_select_or_insert(session,meta.tables[schema + '.' + t], value_d)

                    out_d[t][name_key] = ru_id
                    external_identifiers_to_cdf(session,meta,schema,s.external_identifier_dframe,meta.tables[schema + '.' + t],name_key,ru_id)

                    # for ReportingUnits, deduce and enter composing unit joins
                    if t == 'ReportingUnit':
                        composing_from_reporting_unit_name(session,meta,schema,name_key,ru_id)

            if t == 'Office':
                ## need to process 'Office' after 'ReportingUnit', as Offices may create ReportingUnits as election districts *** check for this
                #%% insert corresponding ReportingUnit, if it doesn'cdf_table already exist.
                for name_key in s.context_dictionary[t]:
                    #%% Check that there is an ElectionDistrictType for the office
                    tt = 'ReportingUnit'
                    if 'ElectionDistrictType' in s.context_dictionary['Office'][name_key].keys():
                        [id,other_txt] = format_type_for_insert(session,meta.tables[schema + '.ReportingUnitType'], s.context_dictionary['Office'][name_key]['ElectionDistrictType'])
                    else:
                        print('Office '+ name_key +' has no associated ElectionDistrictType')
                        bb = 1/0 # TODO

                    #%% Get id for ReportingUnit for the office and enter any associated external identifiers into CDF schema
                    # TODO what if ReportingUnit and/or external identifiers are already there?
                    value_d = {'Name':s.context_dictionary['Office'][name_key]['ElectionDistrict'],'ReportingUnitType_Id':id,'OtherReportingUnitType':other_txt}
                    ru_id = id_from_select_or_insert(session,meta.tables[schema + '.ReportingUnit'], value_d)

                    external_identifiers_to_cdf(session,meta,schema,s.external_identifier_dframe,meta.tables[schema + '.ReportingUnit'],name_key,ru_id)
    session.commit() #  TODO necessary?
    return(out_d)

def context_to_cdf_PANDAS(session,meta,s,schema,cdf_def_dirpath = 'CDF_schema_def_info/'):
    """Takes the info from the text files in the state's context files and inserts it into the db.
    Assumes enumeration tables are already filled.
    """

    # TODO Outline
    context_cdframe = {}    # dictionary of dataframes from context info
    enum_dframe = {}        # dict of dataframes of enumerations, taken from db
    other_id = {}       # dict of the Id for 'other' in the various enumeration tables
    enum_id_d = {}  # maps raw Type string to an Id
    enum_othertype_d = {}  # maps raw Type string to an othertype string
    dframe_for_cdf_db = {}
    # TODO ## context to dataframes
    if not cdf_def_dirpath[-1] == '/': cdf_def_dirpath += '/'
    with open(cdf_def_dirpath+'tables.txt','r') as f:
        table_def_list = eval(f.read())

    for table_def in table_def_list:      # iterating over tables in the common data format schema, need 'Office' after 'ReportingUnit'
        ## need to process 'Office' after 'ReportingUnit', as Offices may create ReportingUnits as election districts *** check for this

        t = table_def[0]      # e.g., cdf_table = 'ReportingUnit'

        # for each table # TODO which tables?
        if t in s.context_dictionary.keys() and t != 'ExternalIdentifier':
            print('\tProcessing ' + t + 's')
            # create DataFrame with enough info to define db table eventually
            if t == 'BallotMeasureSelection':   # note: s.context_dictionary['BallotMeasureSelection'] is a set not a dict
                BallotMeasureSelection_cdframe = pd.DataFrame(list(s.context_dictionary['BallotMeasureSelection']),columns=['Selection'])
            else:
                context_cdframe[t] = pd.read_csv(s.path_to_state_dir + 'context/'+ t + '.txt',sep = '\t')
                for e in table_def[1]['enumerations']:  # e.g., e = "ReportingUnitType"
                    if e not in enum_dframe.keys():
                        enum_id_d[e] = {}  # maps raw Type string to an Id
                        enum_othertype_d[e] = {}  # maps raw Type string to an othertype string

                        #%% pull enumeration table into a DataFrame
                        enum_dframe[e] = pd.read_sql_table(e,session.bind,schema=schema,index_col='Id')
                        #%% find the id for 'other', if it exists
                        try:
                            other_id[e] = enum_dframe[e].index[enum_dframe[e]['Txt'] == 'other'].to_list()[0]
                        except:     # CountItemStatus has no "other" field
                            other_id[e] = None # TODO how does this flow through?
                        #%% create and (partially) fill the id/othertype dictionaries

                    #%% for every instance of the enumeration in the current table (e.g., 'Office'), store corresponding id & othertype in dictionaries
                    if e in context_cdframe[t].columns: # some enumerations (e.g., CountItemStatus for t = ReportingUnit) are not available from context.
                        for v in context_cdframe[t][e].unique(): # e.g., v = 'county' or v = 'precinct'
                            enum_id_d[e][v],enum_othertype_d[e][v] = format_type_for_insert_PANDAS(enum_dframe[e],v,other_id[e])
                        #%% create new id, othertype columns
                        context_cdframe[t][e+'_Id'] = context_cdframe[t][e].map(enum_id_d[e])
                        context_cdframe[t]['Other'+e] = context_cdframe[t][e].map(enum_othertype_d[e])

                if t == 'Office':
                    #%% Check that all ElectionDistrictTypes are recognized
                    for edt in context_cdframe['Office']['ElectionDistrictType'].unique():
                        enum_id_d['ReportingUnitType'][edt], enum_othertype_d['ReportingUnitType'][edt] = format_type_for_insert_PANDAS(enum_dframe['ReportingUnitType'], edt, other_id['ReportingUnitType'])
                        if [enum_id_d['ReportingUnitType'][edt], enum_othertype_d['ReportingUnitType'][edt]] == [None,None]:
                            raise Exception('Office table has unrecognized ElectionDistrictType: ' + edt)

                    #%% insert corresponding ReportingUnits, that don't already exist in db ReportingUnit table.
                    cdf_ReportingUnit_dframe = pd.read_sql_table('ReportingUnit',session.bind,schema)
                    new_ru = []
                    for index, row in context_cdframe['Office'].iterrows():   # TODO more pyhonic/pandic way?
                        if row['ElectionDistrict'] not in cdf_ReportingUnit_dframe.index:
                            new_ru.append ( pd.Series({'Name':row['ElectionDistrict'],'ReportingUnitType_Id':enum_id_d['ReportingUnitType'][row['ElectionDistrictType']],'OtherReportingUnitType':enum_othertype_d['ReportingUnitType'][row['ElectionDistrictType']]}))
                    # %% commit any new ReportingUnits into the db
                    new_ru_dframe = pd.DataFrame(new_ru)
                    new_ru_dframe.to_sql('ReportingUnit', session.bind, schema=schema, if_exists='append', index=False)
                    session.commit()

        #%% commit table to db
        # TODO ## define dframe_for_cdf_db[t]. If we use context_cdframe with right cols added, will old columns be ignored? No.
        if  t != 'ExternalIdentifier':
            df_to_db = context_cdframe[t].copy()
            for c in context_cdframe[t].columns:
                if c not in meta.tables[schema + '.' + t].columns:
                    df_to_db = df_to_db.drop(c,axis = 1)
            df_to_db.to_sql(t,session.bind, schema=schema, if_exists='append', index=False)
            session.commit()
            # Then need to deal with external identifiers, composing reporting units.

        if t == 'ExternalIdentifier':
            # TODO
            pass

    return

def external_identifiers_to_cdf(session,meta,schema,ext_id_dframe,t,name,cdf_id):
    """Insert the external identifiers associated to the item with cdf_id into the CDF schema, .
    ext_id_dframe is a dataframe of external Ids with columns Table,Name,ExternalIdentifierType,ExternalIdentifierValue
    table is a table of the cdf (e.g., ReportingUnit)
    name is the name of the entry (e.g., North Carolina;Alamance County) -- the canonical name for the cdf db
    cdf_id is the id of the named item in the cdf db
    """
    little_dframe = ext_id_dframe[(ext_id_dframe.Table == t.name) & (ext_id_dframe.Name == name)] # this should pick the single row with the right name
    for index, row in little_dframe.iterrows():
        [id,other_txt] = format_type_for_insert(session,meta.tables[schema + '.IdentifierType'],row['ExternalIdentifierType'])
        # [id,other_txt] = format_type_for_insert(schema, 'IdentifierType', row['ExternalIdentifierType']) # TODO remove
        value_d = {'ForeignId':cdf_id,'Value':row['ExternalIdentifierValue'],'IdentifierType_Id':id,'OtherIdentifierType':other_txt}
        ei_t = meta.tables[schema + '.ExternalIdentifier']
        ins = ei_t.insert().values(value_d)
        session.execute(ins)
        #q = 'INSERT INTO {}."ExternalIdentifier" ("ForeignId","Value","IdentifierType_Id","OtherIdentifierType") VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING'  # will this cause errors to go unnoticed? ***
        #dbr.query(q, [schema], [cdf_id, row['ExternalIdentifierValue'], id, other_txt], con, cur)
    session.commit()
    return


def build_munger_d(s,m):
    """given a state s and a munger m,
    use the state's context dictionaries to build some dictionaries restricted to the given munger.
    """
    munger_d = {}
    munger_inverse_d = {}
    key_list = ['Election','Party','ReportingUnit;precinct','Office']   # TODO should this be different for different mungers?
    for t in key_list:
        t_parts = t.split(';')
        context_key = t_parts[0]            # e.g., 'ReportingUnit', or 'Election'
        if len(t_parts) > 1:
            type = t_parts[1]               # e.g., 'precinct' or None
        else:
            type = None
        munger_d[t] = {}
        for k in s.context_dictionary[context_key].keys():  # e.g., k = 'North Carolina;General Assembly;House of Representatives;2019-2020;District 1'
            if 'ExternalIdentifiers' in s.context_dictionary[context_key][k].keys() and   m.name in s.context_dictionary[context_key][k]['ExternalIdentifiers'].keys() and (type == None or s.context_dictionary[context_key][k][context_key+'Type'] == type):
                    munger_d[t][k] = s.context_dictionary[context_key][k]['ExternalIdentifiers'][m.name]
        munger_inverse_d[t] = {}
        for k,v in munger_d[t].items():
            if v in munger_inverse_d[t].keys():
                return('Error: munger_d[\''+t+'\'] has duplicate keys with value '+ v)
            munger_inverse_d[v] = k
    return(munger_d,munger_inverse_d)

def raw_to_context(df,m,munger_d,conn,cur):
    ''' Purely diagnostic -- reports what items in the datafile are missing from the context_dictionary (e.g., offices we don'cdf_table wish to analyze)'''
    print('\'Missing\' below means \'Existing in the datafile, but missing from the munger dictionary, created from the state\'s context_dictionary, which was created from files in the context folder.')
    for t in m.query_from_raw.keys():
        t_parts = t.split(';')
        context_key = t_parts[0]
        if len(t_parts) > 1:
            type = t_parts[1]
        if context_key in df.state.context_dictionary.keys():   # why do we need this criterion? ***
            items_per_df = dbr.query(m.query_from_raw[t],[df.state.schema_name,df.table_name],[],con,cur) # TODO revise now that query_from_raw no longer works
            missing = []
            for e in items_per_df:
                if e[0] is not None and e[0] not in munger_d[t].values():
                    missing.append(e[0])
            if len(missing)>0:
                missing.sort()   #  and sort
            rs.append('Sample data for '+t+': '+str( items_per_df[0:4]))
            rs.append('For \''+m.name +'\', <b> missing '+t+' list is: </b>'+str(missing)+'. Add any missing '+t+' to the '+context_key+'.txt file and rerun')
    return



### supporting routines
def shorten_and_cap_county(normal):
    ''' takes a county name in normal form, strips "County" from the name, and capitalizes'''
    parts=normal.split(';')
    
    parser = re.compile('^(?P<short_name>[^\n\t]+)\ County')
    return(parser.search(parts[1]).group('short_name').upper())

def add_externalidentifier(dict,id_type):
    '''input is a dictionary whose keys are county names in normal form and values are dictionaries, including identifiertype-identifier pairs, and an identifiertype. Output is same dictionary, with the identifiers (short name, all caps) included, labeled by the given id_type.'''
    for k in dict.keys():
        if dict[k]['Type'] == 'county':
            print(k)
            dict[k]['ExternalIdentifiers'][id_type]=shorten_and_cap_county(k)
    return(dict)
        
def dict_insert(dict_file_path,input_d):
    '''Insert the objects in the dictionary (input_d) into the dictionary stored in the file (at dict_file_path), updating each ExternalIdentifiers dict and any new info, throwing error if the dictionaries conflict'''
    with open(dict_file_path,'r') as f:
        file_d = eval(f.read())
    for k in input_d.keys():
        if k in file_d.keys():
            for kk in input_d[k].keys():
                if kk == 'ExternalIdentifiers':  # update external identifiers, checking for conflict
                    for kkk in input_d[k]['ExternalIdentifiers'].keys():
                        if kkk in file_d[k]['ExternalIdentifiers'].keys():
                            if input_d[k]['ExternalIdentifiers'][kkk] != file_d[k]['ExternalIdentifiers'][kkk]:
                                print('Error: ExternalIdentifiers conflict on ' + kkk)
                                sys.exit()
                        else:
                             file_d[k]['ExternalIdentifiers'][kkk] = input_d[k]['ExternalIdentifiers'][kkk]
                else:   # for properties of the item other than External Idenifiers
                    if kk in file_d[k].keys():
                        if input_d[k][kk] != file_d[k][kk]:
                            print('Error: conflict on ' + kk)
                            sys.exit()
                    else:
                        file_d[k][kk]=input_d[k][kk]
        else:
            file_d[k] = input_d[k]    # put input_d info into file_d
    with open(dict_file_path,'w') as f:
            f.write(str(file_d))
    return(file_d)


def insert_reporting_unit(dict,reporting_unit_list,id_type):
    '''Insert the reporting units in reporting_unit_list (list of unit, type pairs) into dict, with correct type (e.g., precinct) and recording the name of the reporting unit also as an external identifier, unless the reporting unit is already in the dict, in which case do the right thing. '''
    for r in reporting_unit_list:
        k = r[0]    # Reporting unit
        t = r[1]    # Type
        if k not in dict.keys():    # if reporting unit not already in dictionary, add it
            dict[k]={'Type':t,'ExternalIdentifiers':{id_type:k}}
        elif dict[k]['Type'] != t: # if reporting type is in the dictionary, but has different 'Type'
            t_dict = dict[k]['Type']
            dict[r+' ('+  t_dict   +')'] = dict.pop(r) # rename existing key to include type (e.g., precinct)
            dict[r+' ('+  reporting_unit_type   +')'] = {'Type':t,'ExternalIdentifiers':{id_type:r}}
            
def extract_precincts(s,df):
    ''' s is a state; df is a datafile with precincts (*** currently must be in the format of the nc_pct_results file; need to read info from metafile) '''
    if s != df.state:   # consistency check: file must belong to state
        print('Datafile ' +df+ ' belongs to state '+df.state.name+', not to '+s.name)
    rep_unit_list=[]
    with open(s.path_to_state_dir+'data/'+df.file_name,'r') as f:
        lines=f.readlines()
    for line in lines[1:]:
        fields = line.strip('\n\r').split('\t')
        real_precinct=fields[14]
        if real_precinct == 'Y':     # if row designated a "real precinct" in th nc file
            county = fields[0]
            precinct = fields[2]
            rep_key = s.name+';'+county.capitalize()+' County;Precinct '+precinct
            rep_unit_list.append([rep_key,'precinct'])  # return key and 'Type'
        elif real_precinct == 'N':
            county = fields[0]
            election = fields[1]
            precinct = fields[2]
            rep_key = s.name+';'+county.capitalize()+' County;'+election+';'+precinct
            rep_unit_list.append([rep_key,'other;'+rep_key])
    return(rep_unit_list)
    

    
def insert_offices(s,d):
    ''' s is a state; d is a dictionary giving the number of districts for standard offices within the state, e.g., {'General Assembly;House of Representatives':120,'General Assembly;Senate':50} for North Carolina. Returns dictionary of offices. '''
    state = s.name
    out_d = {}
    for k in d.keys():
        for i in range(d[k]):
            office_name = state + ';' + k +';District ' + str(i+1)
            out_d[office_name] = {'ElectionDistrict':office_name}
    out_d['North Carolina;US Congress;Senate']={'ElectionDistrict':'North Carolina'}
    dict_insert(s.path_to_state_dir + 'context/Office.txt',out_d)
    return(out_d)
    



# is this still necessary?
def process(nc_pct_results_file_path,dict_file_path,outfile):
    a = extract_precincts(nc_pct_results_file_path)
    with open(dict_file_path,'r') as f:
        d=eval(f.read())
    insert_reporting_unit(d,a,'nc_export1')
    with open(outfile,'w') as f:
        f.write(str(d))


## temporary election_anomaly to fix nc_export1 reporting unit ExternalIdentifiers

def fix(fp):        # fp is the path to the reporting_unit.txt file
    with open(fp,'r') as f:
        d= eval(f.read())
    for k in d.keys():
        if d[k]['Type'][:6] == 'other;':
            d[k]['ExternalIdentifiers']['nc_export1']  # remove old
            sections = k.split(';')
            county_key = sections[1]
            nc_export1_county = shorten_and_cap_county(k)
            #p = re.compile('^Precinct (?P<precinct>.+)$')
            #m = p.search(sections[2])
            #precinct = m.group('precinct')
            precinct = sections[3]
            d[k]['ExternalIdentifiers']['nc_export1'] = nc_export1_county+';'+precinct
    with open(fp+'.new','w') as f:
        f.write(str(d))

if __name__ == '__main__':
    from sqlalchemy.orm import sessionmaker
    import states_and_files as sf

    schema='test'
    eng,meta = dbr.sql_alchemy_connect(schema=schema,paramfile='../../local_data/database.ini')
    Session = sessionmaker(bind=eng)
    session = Session()

    s = sf.create_state('NC','../../local_data/NC/')

    context_to_cdf_PANDAS(session,meta,s,schema,cdf_def_dirpath='../CDF_schema_def_info/')
    print('Done!')


