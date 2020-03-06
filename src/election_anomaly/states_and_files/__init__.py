#!usr/bin/python3
import os.path
import db_routines as dbr
import pandas as pd
class State:
    def create_db_and_schemas(self):
        # create db
        con = dbr.establish_connection()
        cur = con.cursor()
        dbr.create_database(con,cur,self.short_name)
        cur.close()
        con.close()
        # connect to  and create the three schemas
        con = dbr.establish_connection(db_name=self.short_name)
        cur = con.cursor()
        q = "CREATE SCHEMA context;"
        dbr.query(q,[],[],con,cur)
        q = "CREATE SCHEMA cdf;"
        dbr.query(q,[],[],con,cur)
        cur.close()
        con.close()
        return

    def __init__(self,short_name,path_to_parent_dir):        # reporting_units,elections,parties,offices):
        """ short_name is the name of the directory containing the state info, including data,
         and is used other places as well.
         path_to_parent_dir is the parent directory of dir_name
        """
        self.short_name = short_name
        if path_to_parent_dir[-1] != '/':     # should end in /
            path_to_parent_dir += '/'
        self.path_to_state_dir= path_to_parent_dir + short_name+'/'
        assert os.path.isdir(self.path_to_state_dir), 'Error: No directory '+ self.path_to_state_dir
        assert os.path.isdir(self.path_to_state_dir+'context/'), 'Error: No directory '+ self.path_to_state_dir+'context/'
        # Check that context directory is missing no files
        context_file_list = ['Election.txt','Office.txt','remark.txt','ReportingUnit.txt']
        file_missing_list = [f for f in context_file_list if not os.path.isfile(self.path_to_state_dir+'context/'+f)]
        assert file_missing_list == [], 'Error: Missing files in '+ self.path_to_state_dir+'context/:\n'+ str(file_missing_list)
        # TODO format string above '...'.format()
class Munger:

    def check_new_datafile(self,f):
        """f is a results datafile; this routine should add what's necessary to the munger to treat the datafile,
        keeping backwards compatibility and exiting gracefully if datafile needs different munger"""
        # TODO check that columns of f are all in raw_columns.txt
        # TODO
        return

    def find_unmatched(self,f,element):
        """find any instances of <element> referenced in <f> but not interpretable by <self>"""

        # get list of columns of <f> needed to determine the ExternalIdentifier for <element>
        p='\<([^\>]+)\>'
        col_list=re.findall(p,self.cdf_tables.loc[element,'raw_identifier'])

        # create dataframe of unique instances of <element>
        f_elts=f[col_list].drop_duplicates()

        # munge the given element into a new column of f_elts
        add_munged_column(f_elts,self,element,element)

        # identify instances that are not matched in the munger's ExternalIdentifier table



        # save any unmatched elements (if drop_unmatched=False)
        unmatched = row_df[row_df['raw_identifier_value'].isnull()].loc[:,table_name + '_external'].unique()
        if unmatched.size > 0:
            unmatched_path = unmatched_dir + 'unmatched_' + table_name + '.txt'
            np.savetxt(unmatched_path,unmatched,fmt="%s")
            print(
                'WARNING: Some elements unmatched, saved to {}.\nIF THESE ELEMENTS ARE NECESSARY, USER MUST put them in both the munger ExternalIdentifier.txt and in the {}.txt file in the context directory'.format(
                    unmatched_path,table_name))
        # TODO
        # return

    def __init__(self,dir_path):
        assert os.path.isdir(dir_path),'Not a directory: ' + dir_path
        assert os.path.isfile(dir_path + 'cdf_tables.txt') and os.path.isfile(dir_path + 'atomic_reporting_unit_type.txt') and os.path.isfile(
            dir_path + 'count_columns.txt') , \
            'Directory {} must contain files atomic_reporting_unit_type.txt, cdf_tables.txt, count_columns.txt'.format(dir_path)
        self.name=dir_path.split('/')[-2]    # 'nc_general'

        if dir_path[-1] != '/':
            dir_path += '/' # make sure path ends in a slash
        self.path_to_munger_dir=dir_path

        # read raw_identifiers file into a table
        self.raw_identifiers=pd.read_csv('{}raw_identifiers.txt'.format(dir_path),sep='\t') # note no natural index column

        # define dictionary to change any column names that match internal CDF names
        with open('CDF_schema_def_info/tables.txt','r') as f:
            table_list = eval(f.read())
        col_d = dict([[x[0],'{}_{}'.format(x[0],self.name)] for x in table_list])
        self.rename_column_dictionary=col_d

        # read raw columns from file (renaming if necessary)
        self.raw_columns = pd.read_csv('{}raw_columns.txt'.format(dir_path),sep='\t').replace({'name':col_d})

        # read cdf tables and rename in ExternalIdentifiers col if necessary
        cdft=pd.read_csv('{}cdf_tables.txt'.format(dir_path),sep='\t',index_col='cdf_element')  # note index
        for k in col_d.keys():
            cdft['raw_identifier'] = cdft['raw_identifier'].str.replace('\<{}\>'.format(k),'<{}>'.format(col_d[k]))
        self.cdf_tables = cdft

        # determine how to treat ballot measures (ballot_measure_style)
        bms=pd.read_csv('{}ballot_measure_style.txt'.format(dir_path),sep='\t')
        assert 'short_name' in bms.columns, 'ballot_measure_style.txt does not have required column \'short_name\''
        assert 'truth' in bms.columns, 'ballot_measure_style.txt does not have required column \'truth\''
        self.ballot_measure_style=bms[bms['truth']]['short_name'].iloc[0]    # TODO error handling. This takes first line  marked "True"

        # determine whether the file has columns for counts by vote types, or just totals
        count_columns=pd.read_csv('{}count_columns.txt'.format(dir_path),sep='\t').replace({'RawName':col_d})
        self.count_columns=count_columns
        if list(count_columns['CountItemType'].unique()) == ['total']:
            self.totals_only=True
        else:
            self.totals_only=False

        if self.ballot_measure_style == 'yes_and_no_are_candidates':
            with open('{}ballot_measure_selections.txt'.format(dir_path),'r') as f:
                selection_list=f.readlines()
            self.ballot_measure_selection_list = [x.strip() for x in selection_list]


            bms_str=cdft.loc['BallotMeasureSelection','raw_identifier']
            # note: bms_str will start and end with <>
            self.ballot_measure_selection_col = bms_str[1:-1]
        else:
            self.ballot_measure_selection_list=None # TODO is that necessary?

        with open('{}atomic_reporting_unit_type.txt'.format(dir_path),'r') as f:
            self.atomic_reporting_unit_type = f.readline()
