import os
from trex_astf_lib.trex_astf_client import *   # noqa: ignore=F403
from trex_astf_lib.trex_astf_exceptions import *   # noqa: ignore=F403
from trex_astf_lib.cap_handling import *   # noqa: ignore=F403
from trex_astf_lib.sim import main as sim_main
import functional_general_test
from nose.plugins.attrib import attr


@attr('run_on_trex')
class CNstfPcap_Test(functional_general_test.CGeneralFunctional_Test):
    def setUp(self):
        sys.path.append("../../astf")

    def compare_l7(self, cap1, cap2):
        cap1_reader = CPcapReader(cap1)
        cap1_reader.analyze()
        cap1_reader.condense_pkt_data()
        cap2_reader = CPcapReader(cap2)
        cap2_reader.analyze()
        cap2_reader.condense_pkt_data()

        num = cap1_reader.is_same_pkts(cap2_reader)
        if num != -1:
            print("Error comparing cap files. pkt number {0} is different".format(num))
            print("{0} is:".format(cap1))
            cap1_reader.dump()
            print("{0} is:".format(cap2))
            cap1_reader.dump()
            sys.exit(1)

    def handle_one_cap(self, cap_file_name):
        profile = """
from trex_astf_lib.api import ASTFProfile, ASTFCapInfo, ASTFIPGenDist, ASTFIPGen
class Prof1():
    def __init__(self):
        pass
    def get_profile(self):
        ip_gen_c = ASTFIPGenDist(ip_range=["16.0.0.1", "16.0.0.255"], distribution="seq")
        ip_gen_s = ASTFIPGenDist(ip_range=["48.0.0.1", "48.0.255.255"], distribution="seq")
        ip_gen = ASTFIPGen(dist_client=ip_gen_c, dist_server=ip_gen_s)
        return ASTFProfile(default_ip_gen=ip_gen, cap_list=[ASTFCapInfo(file="%s")])

def register():
    return Prof1()
"""
        prof_file_name = "../../astf/" + cap_file_name.split('/')[-1].split('.')[0]
        p = profile % ("../" + cap_file_name)
        f = open(prof_file_name+".py", 'w')
        f.write(p)
        f.close()

        sim_main(args=["-p", "../..", "-f", prof_file_name+".py", "-o", "../../exp/astf_test_out"])
        self.compare_l7("../../" + cap_file_name, "../../exp/astf_test_out_c.pcap")
        self.compare_l7("../../" + cap_file_name, "../../exp/astf_test_out_s.pcap")
        os.remove(prof_file_name + ".py")
        try:
            os.remove(prof_file_name + ".pyc")
        except FileNotFoundError:
            pass
        os.remove("../../exp/astf_test_out_c.pcap")
        os.remove("../../exp/astf_test_out_s.pcap")

    def check_one_cap(self, file):
        self.handle_one_cap(file)

    def test_caps(self):
        files = ["avl/delay_10_http_browsing_0.pcap"]
        for file in files:
            self.check_one_cap(file)


@attr('run_on_trex')
class CNstfBasic_Test(functional_general_test.CGeneralFunctional_Test):
    def reset(self):
        ASTFIPGenDist.class_reset()
        ASTFProgram.class_reset()
        ASTFTCPInfo.class_reset()

    def compare_json(self, json1, json2):
        if json1 != json2:
            print ("Error {0} and {1} differ".format(json1, json2))
            return False
        return True

    def test_ASTFProgram(self):
        expect_class_json = [u'YWFh', u'YmJi']
        expect_prog_json = {'commands': [{'name': 'tx', 'buf_index': 0}, {'min_bytes': 100, 'name': 'rx'},
                                         {'delay': 3, 'name': 'delay'}, {'name': 'tx', 'buf_index': 0},
                                         {'name': 'tx', 'buf_index': 1}, {'name': 'reset'}]}

        prog = ASTFProgram()
        prog.send("aaa")
        prog.recv(100)
        prog.delay(3)
        prog.send("aaa")
        prog.send("bbb")
        prog.reset()
        class_json = ASTFProgram.class_to_json()
        prog_json = prog.to_json()

        assert(self.compare_json(class_json, expect_class_json))
        assert(self.compare_json(prog_json, expect_prog_json))

    def test_ASTFIPGenDist(self):
        class_json = [{'distribution': 'seq', 'ip_end': '16.0.0.255', 'ip_start': '16.0.0.1'},
                      {'distribution': 'rand', 'ip_end': '1.1.1.255', 'ip_start': '1.1.1.1'}]

        default_to_json = {'index': 0}
        non_default_to_json = {'index': 1}

        # bad pair
        try:
            bad_ip_gen = ASTFIPGenDist(ip_range="1.1.1.1")
        except ASTFError as e:
            assert (type(e) == ASTFErrorBadIpRange)
        else:
            assert 0, "Bad exception, or no exception"

        # bad pair 2
        try:
            bad_ip_gen = ASTFIPGenDist(ip_range=["1.1.1.1", "1.2.3.300"])
        except ASTFError as e:
            assert (type(e) == ASTFErrorBadIpRange)
        else:
            assert 0, "Bad exception, or no exception"

        # bad distribution
        try:
            bad_ip_gen = ASTFIPGenDist(ip_range=["1.1.1.1", "1.2.3.5"], distribution="aa")  # noqa: ignore=F841
        except ASTFError as e:
            assert (type(e) == ASTFError)
        else:
            assert 0, "Bad exception, or no exception"

        default_ip_gen = ASTFIPGenDist(ip_range=['16.0.0.1', '16.0.0.255'])
        non_default_ip_gen = ASTFIPGenDist(ip_range=["1.1.1.1", "1.1.1.255"], distribution="rand")

        assert(self.compare_json(class_json, ASTFIPGenDist.class_to_json()))
        assert(self.compare_json(default_to_json, default_ip_gen.to_json()))
        assert(self.compare_json(non_default_to_json, non_default_ip_gen.to_json()))

    def test_ASTFIPGenGlobal(self):
        # bad IP
        try:
            bad_ip = ASTFIPGenGlobal(ip_offset="1.2.3.300")  # noqa: ignore=F841
        except ASTFError as e:
            assert (type(e) == ASTFErrorBadIp)
        else:
            assert 0, "Bad exception, or no exception"

    def test_ASTFTCPInfo(self):
        class_json = [{'window': 32768, 'options': 0, 'port': 80}, {'window': 100, 'options': 0, 'port': 8080}]
        json1 = {'index': 1}
        json2 = {'index': 0}

        # bad side
        try:
            tcp_info = ASTFTCPInfo(side="t")  # noqa: ignore=F841
        except ASTFError as e:
            assert (type(e) == ASTFError)
        else:
            assert 0, "Bad exception, or no exception"

        # default arguments test
        tcp_info = ASTFTCPInfo(side="c")
        assert (tcp_info.window == ASTFTCPInfo.DEFAULT_WIN)
        assert (tcp_info.port == ASTFTCPInfo.DEFAULT_PORT)

        tcp_info1 = ASTFTCPInfo(side="c", window=100, port=8080)
        tcp_info2 = ASTFTCPInfo(side="c", window=ASTFTCPInfo.DEFAULT_WIN)

        assert(self.compare_json(class_json, ASTFTCPInfo.class_to_json()))
        assert(self.compare_json(json1, tcp_info1.to_json()))
        assert(self.compare_json(json2, tcp_info2.to_json()))

    def test_ASTFAssociationRule(self):
        json = {'ip_end': '2.2.2.2', 'port': 80, 'ip_start': '1.1.1.1'}

        assoc_rule = ASTFAssociationRule(ip_start="1.1.1.1", ip_end="2.2.2.2")
        assert(self.compare_json(json, assoc_rule.to_json()))

    def test_ASTFAssociation(self):
        json = [{'ip_end': '2.2.2.2', 'port': 8080, 'ip_start': '1.1.1.1'},
                {'ip_end': '4.2.2.2', 'port': 80, 'ip_start': '3.1.1.1'}]
        assoc_rule1 = ASTFAssociationRule(ip_start="1.1.1.1", ip_end="2.2.2.2", port=8080)
        assoc_rule2 = ASTFAssociationRule(ip_start="3.1.1.1", ip_end="4.2.2.2")

        assoc = ASTFAssociation([assoc_rule1, assoc_rule2])
        assert(self.compare_json(json, assoc.to_json()))

    def test_ASTFTCPClientTemplate(self):
        json = {'tcp_info': {'index': 0}, 'cluster': {}, 'program_index': 0, 'cps': 1, 'port': 80,
                'ip_gen': {'dist_client': {'index': 0}, 'dist_server': {'index': 1}}}

        # no program
        try:
            c_temp = ASTFTCPServerTemplate()
        except ASTFError as e:
            assert type(e) == ASTFErrorMissingParam
        else:
            assert 0, "Bad exception, or no exception"

        # Valid client template
        prog = ASTFProgram()
        prog.send("ttt")
        ip_gen_c = ASTFIPGenDist(ip_range=["16.0.0.1", "16.0.0.255"], distribution="seq")
        ip_gen_s = ASTFIPGenDist(ip_range=["48.0.0.1", "48.0.255.255"], distribution="seq")
        ip_gen = ASTFIPGen(dist_client=ip_gen_c, dist_server=ip_gen_s)
        c_temp = ASTFTCPClientTemplate(ip_gen=ip_gen, program=prog)

        assert(self.compare_json(json, c_temp.to_json()))

    def test_ASTFTCPServerTemplate(self):
        json = {'program_index': 0, 'assoc': [{'port': 80}], 'tcp_info': {'index': 0}}
        template_json = [{'commands': [{'name': 'tx', 'buf_index': 0}]}, {'commands': [{'name': 'tx', 'buf_index': 1}]}]
        prog_json = [u'eXl5', u'YWFh']

        # no program
        try:
            s_temp = ASTFTCPServerTemplate()
        except ASTFError as e:
            assert type(e) == ASTFErrorMissingParam
        else:
            assert 0, "Bad exception, or no exception"

        # Valid server template
        prog = ASTFProgram()
        prog.send("yyy")
        s_temp = ASTFTCPServerTemplate(program=prog)
        assert(self.compare_json(json, s_temp.to_json()))

        # Same template as prev
        prog2 = ASTFProgram()
        prog2.send("yyy")
        s_temp2 = ASTFTCPServerTemplate(program=prog2)
        assert(self.compare_json(json, s_temp2.to_json()))

        # Different template
        prog3 = ASTFProgram()
        prog3.send("aaa")
        s_temp3 = ASTFTCPServerTemplate(program=prog3)
        json['program_index'] = 1  # now we expect program index to be 1
        assert(self.compare_json(json, s_temp3.to_json()))
        assert(self.compare_json(template_json, ASTFTCPServerTemplate.class_to_json()))
        assert(self.compare_json(prog_json, ASTFProgram.class_to_json()))

    def test_ASTFCapInfo(self):
        # no file
        try:
            cap_info = ASTFCapInfo()
        except ASTFError as e:
            assert type(e) == ASTFErrorMissingParam
        else:
            assert 0, "Bad exception, or no exception"

        # L7 and CPS
        try:
            cap_info = ASTFCapInfo(file="/tmp/not_exist", cps=1, l7_percent=7)  # noqa: ignore=F841
        except ASTFError as e:
            assert type(e) == ASTFErrorBadParamCombination
        else:
            assert 0, "Bad exception, or no exception"

    def test_ASTFProfile(self):
        ip_gen_c = ASTFIPGenDist(ip_range=["16.0.0.1", "16.0.0.255"], distribution="seq")
        ip_gen_s = ASTFIPGenDist(ip_range=["48.0.0.1", "48.0.255.255"], distribution="seq")
        ip_gen = ASTFIPGen(dist_client=ip_gen_c, dist_server=ip_gen_s)

        # Missing parameters
        try:
            prof = ASTFProfile(default_ip_gen=ip_gen)
        except ASTFError as e:
            assert type(e) == ASTFErrorMissingParam
        else:
            assert 0, "Bad exception, or no exception"

        # specifying both templates and cap_list
        prog = ASTFProgram()
        prog.send("yyy")
        c_temp = ASTFTCPClientTemplate(program=prog, ip_gen=ip_gen)
        s_temp = ASTFTCPServerTemplate(program=prog)
        template = ASTFTemplate(client_template=c_temp, server_template=s_temp)
        try:
            prof = ASTFProfile(default_ip_gen=ip_gen,   # noqa: ignore=F841
                templates=template, cap_list=ASTFCapInfo(file="/tmp/aaa"))
        except ASTFError as e:
            assert type(e) == ASTFErrorBadParamCombination
        else:
            assert 0, "Bad exception, or no exception"

    def setUp(self):
        self.reset()

    def test_astf(self):
        pass