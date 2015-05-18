###########################################################
#
# Copyright (c) 2005, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#

__all__ = ["WorkflowTest"]

import tacticenv

import unittest, random


from pyasm.unittest import UnittestEnvironment, Sample3dEnvironment
from pyasm.search import Search, SearchType
from pyasm.command import Command, Trigger

from workflow import *

from pyasm.security import Batch



class WorkflowTest(unittest.TestCase):

    def test_all(my):
        Batch()
        from pyasm.web.web_init import WebInit

        test_env = UnittestEnvironment()
        test_env.create()

        try:
            my._test_complete_trigger()
        finally:
            test_env.delete()
 
 
    def _test_complete_trigger(my):
        cmd = WorkflowCmd()
        Command.execute_cmd(cmd)


class WorkflowCmd(Command):
    def execute(my):

        #from pyasm.security import Site
        #from pyasm.biz import Project
        #print "site: " ,Site.get_site()
        #print "project: ", Project.get().get_data()

        try:
            workflow_init()
            my._test_auto_process()
            my._test_check()
            my._test_choice()
        except Exception, e:
            print "Error: ", e
            raise


    def get_pipeline(my, pipeline_xml, add_tasks=False):

        pipeline = SearchType.create("sthpw/pipeline")
        pipeline.set_pipeline(pipeline_xml)
        pipeline_id = random.randint(0, 10000000)
        pipeline.set_value("code", "test%s" % pipeline_id)
        pipeline.set_id(pipeline_id)
        pipeline.set_value("id", pipeline_id)
        pipeline.set_value("pipeline", pipeline_xml)

        process_names = pipeline.get_process_names()

        # delete the processes
        search = Search("config/process")
        search.add_filters("process", process_names)
        processes = search.get_sobjects()
        for process in processes:
            process.delete()

        # create new processes
        processes_dict = {}
        for process_name in process_names:

            # define the process nodes
            process = SearchType.create("config/process")
            process.set_value("process", process_name)
            process.set_value("pipeline_code", pipeline.get_code())
            process.commit()

            processes_dict[process_name] = process


            # Note: we don't have an sobject yet
            if add_tasks:
                task = SaerchType.create("sthpw/task")
                task.set_parent(sobject)
                task.set_value("process", process_name)
                task.commit()


        return pipeline, processes_dict



    def _test_auto_process(my):

        # create a dummy sobject
        sobject = SearchType.create("sthpw/virtual")
        sobject.set_value("code", "test")
        sobject.set_value("a", False)
        sobject.set_value("b", False)
        sobject.set_value("c", False)
        sobject.set_value("d", False)
        sobject.set_value("e", False)

        pipeline_xml = '''
        <pipeline>
          <process type="auto" name="a"/>
          <process type="auto" name="b"/>
          <process type="auto" name="c"/>
          <process type="auto" name="d"/>
          <process type="auto" name="e"/>
          <connect from="a" to="b"/>
          <connect from="b" to="c"/>
          <connect from="b" to="d"/>
          <connect from="c" to="e"/>
          <connect from="d" to="e"/>
        </pipeline>
        '''
        pipeline, processes = my.get_pipeline(pipeline_xml)

        for process in processes.keys():
            a_process = processes.get(process)
            a_process.set_json_value("trigger", {
                'on_complete': '''
                #print "complete: ", process
                sobject.set_value('%s', "complete")
                ''' % process
            } )
            a_process.commit()

        process = "a"
        output = {
            "pipeline": pipeline,
            "sobject": sobject,
            "process": process
        }

        import time
        start = time.time()
        Trigger.call(my, "process|pending", output)
        #print "time: ", time.time() - start
        my.assertEquals( "complete", sobject.get_value("a"))
        my.assertEquals( "complete", sobject.get_value("b"))
        my.assertEquals( "complete", sobject.get_value("c"))
        my.assertEquals( "complete", sobject.get_value("d"))

        # TODO: this got called twice ... not what we want : fix later
        my.assertEquals( "complete", sobject.get_value("e"))



    def _test_check(my):

        # create a dummy sobject
        sobject = SearchType.create("sthpw/virtual")
        sobject.set_value("code", "test")
        sobject.set_value("a", False)
        sobject.set_value("b", False)
        sobject.set_value("c", False)

        # simple condition
        pipeline_xml = '''
        <pipeline>
          <process type="auto" name="a"/>
          <process type="condition" name="b"/>
          <process type="auto" name="c"/>
          <connect from="a" to="b"/>
          <connect from="b" to="c" from_attr="success"/>
          <connect from="b" to="a" from_attr="fail"/>
        </pipeline>

        '''

        pipeline, processes = my.get_pipeline(pipeline_xml)

        for process in processes.keys():
            a_process = processes.get(process)
            a_process.set_json_value("trigger", {
                'on_complete': '''
                sobject.set_value('%s', "complete")
                ''' % process,
                'on_revise': '''
                sobject.set_value('%s', "revise")
                ''' % process
            } )
            a_process.commit()


        process = processes.get("b")
        process.set_json_value("trigger", {
            'on_action': '''
            # ... some code to determine True or False
            return False
            '''
        } )
        process.commit()


        # Run the pipeline
        process = "a"
        output = {
            "pipeline": pipeline,
            "sobject": sobject,
            "process": process
        }
        Trigger.call(my, "process|pending", output)
        my.assertEquals( "revise", sobject.get_value("a"))


        process = processes.get("b")
        process.set_json_value("trigger", {
            'on_action': '''
            # ... some code to determine True or False
            return True
            ''',
            'on_complete': '''
            sobject.set_value('%s', "complete")
            '''
 
        } )
        process.commit()


        # Run the pipeline
        process = "a"
        output = {
            "pipeline": pipeline,
            "sobject": sobject,
            "process": process
        }
        Trigger.call(my, "process|pending", output)
        my.assertEquals( "complete", sobject.get_value("a"))
        my.assertEquals( "complete", sobject.get_value("c"))




    def _test_choice(my):

        # create a dummy sobject
        sobject = SearchType.create("sthpw/virtual")
        sobject.set_value("code", "test")
        sobject.set_value("a", False)
        sobject.set_value("b", False)
        sobject.set_value("c", False)
        sobject.set_value("d", False)
        sobject.set_value("e", False)


        pipeline_xml = '''
        <pipeline>
          <process type="auto" name="a"/>
          <process type="condition" name="b"/>
          <process type="auto" name="c"/>
          <process type="auto" name="d"/>
          <process type="auto" name="e"/>
          <connect from="a" to="b"/>
          <connect from="b" to="c" from_attr="stream1"/>
          <connect from="b" to="d" from_attr="stream2"/>
          <connect from="b" to="e" from_attr="stream3"/>
        </pipeline>

        '''

        pipeline, processes = my.get_pipeline(pipeline_xml)

        for process in processes.keys():
            a_process = processes.get(process)
            a_process.set_json_value("trigger", {
                'on_complete': '''
                sobject.set_value('%s', "complete")
                ''' % process,
            } )
            a_process.commit()


        process = processes.get("b")
        process.set_json_value("trigger", {
            'on_action': '''
            # ... some code to determine True or False
            return ['stream1', 'stream3']
            ''',
            'on_complete': '''
            sobject.set_value('b', "complete")
            '''
        } )
        process.commit()


        # Run the pipeline
        process = "a"
        output = {
            "pipeline": pipeline,
            "sobject": sobject,
            "process": process
        }
        Trigger.call(my, "process|pending", output)

        my.assertEquals( "complete", sobject.get_value("a"))
        my.assertEquals( "complete", sobject.get_value("b"))
        my.assertEquals( "complete", sobject.get_value("c"))
        my.assertEquals( False, sobject.get_value("d"))
        my.assertEquals( "complete", sobject.get_value("e"))







    def assertEquals(my, a, b):
        if a == b:
            return
        else:
            raise Exception("%s != %s" % (a,b))


def main():
    # Not sure why the unit test doesn't activate the trigger system
    unittest.main()
    #cmd = WorkflowCmd()
    #Command.execute_cmd(cmd)




if __name__ == '__main__':
    main()





