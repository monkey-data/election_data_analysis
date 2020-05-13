import states_and_files as sf
import os
import user_interface as ui
import munge_routines as mr
import db_routines as dbr
from sqlalchemy.orm import sessionmaker


if __name__ == '__main__':

	project_root = '/Users/Steph-Airbook/Documents/CampaignScientific/NSF2019/State_Data/results_analysis/src/'



	# pick munger (nb: session=None by default, so info pulled from file system, not db)
	munger = ui.pick_munger(mungers_dir=os.path.join(project_root,'mungers'),project_root=project_root)

	exit()