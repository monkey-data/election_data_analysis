import db_routines as dbr
import user_interface as ui
from sqlalchemy.orm import sessionmaker
import tkinter as tk
import os


if __name__ == '__main__':
	print("""Ready to load some election result data?
			"This program will walk you through the process of creating or checking
			"an automatic munger that will load your data into a database in the 
			"NIST common data format.""")

	project_root = ui.get_project_root()

	# initialize root widget for tkinter
	tk_root = tk.Tk()

	# pick jurisdiction
	juris = ui.pick_juris_from_filesystem(project_root)

	# pick db to use
	db_paramfile = ui.pick_paramfile()
	db_name = ui.pick_database(project_root,db_paramfile)

	# connect to db
	eng, meta = dbr.sql_alchemy_connect(paramfile=db_paramfile,db_name=db_name)
	Session = sessionmaker(bind=eng)
	sess = Session()

	# pick munger
	munger = ui.pick_munger(mungers_dir=os.path.join(project_root,'mungers'),
							project_root=project_root,session=sess)

	# get datafile & info
	[dfile_d, enum_d, data_path] = ui.pick_datafile(project_root,sess)

	# check munger against datafile.
	munger.check_against_datafile(data_path)

	# TODO check datafile/munger against db?

	# load new datafile
	ui.new_datafile(
		sess,munger,data_path,juris=juris,project_root=project_root)

	eng.dispose()
	print('Done! (user_interface)')

	exit()