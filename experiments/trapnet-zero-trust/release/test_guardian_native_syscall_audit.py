import unittest
import guardian_native_syscall_audit as audit

BINARY="/tmp/guardian-test"
class AuditTraceParserTests(unittest.TestCase):
    def test_valid_exact_initial_exec(self):
        raw='1234 execve("/tmp/guardian-test", ["guardian"], 0x123) = 0\n1234 +++ exited with 0 +++\n'
        v=audit.inspect_trace(raw,BINARY)
        self.assertEqual(v["initial_execve"],1)
        self.assertEqual(v["network_syscalls"],0)
    def test_pid_brackets_supported(self):
        raw='[pid 123] execve("/tmp/guardian-test", [], []) = 0\n'
        self.assertEqual(audit.inspect_trace(raw,BINARY)["initial_execve"],1)
    def test_network_socket_refused(self):
        raw='123 execve("/tmp/guardian-test", [], []) = 0\n123 socket(AF_INET, SOCK_STREAM, IPPROTO_TCP) = 4\n'
        with self.assertRaises(ValueError):audit.inspect_trace(raw,BINARY)
    def test_connect_refused(self):
        raw='execve("/tmp/guardian-test", [], []) = 0\nconnect(4, {sa_family=AF_INET}, 16) = -1 ECONNREFUSED\n'
        with self.assertRaises(ValueError):audit.inspect_trace(raw,BINARY)
    def test_process_exec_refused(self):
        raw='execve("/tmp/guardian-test", [], []) = 0\nexecve("/bin/sh", [], []) = 0\n'
        with self.assertRaises(ValueError):audit.inspect_trace(raw,BINARY)
    def test_execveat_refused(self):
        raw='execve("/tmp/guardian-test", [], []) = 0\nexecveat(AT_FDCWD, "/bin/sh", [], [], 0) = 0\n'
        with self.assertRaises(ValueError):audit.inspect_trace(raw,BINARY)
    def test_empty_trace_refused(self):
        with self.assertRaises(ValueError):audit.inspect_trace("",BINARY)
    def test_unexpected_initial_binary_refused(self):
        with self.assertRaises(ValueError):
            audit.inspect_trace('execve("/tmp/evil", [], []) = 0',BINARY)
    def test_multiple_initial_exec_refused(self):
        raw='execve("/tmp/guardian-test", [], []) = 0\nexecve("/tmp/guardian-test", [], []) = 0\n'
        with self.assertRaises(ValueError):audit.inspect_trace(raw,BINARY)
    def test_unrecognized_output_refused(self):
        with self.assertRaises(ValueError):
            audit.inspect_trace('strace: dropped event',BINARY)
    def test_accepted_signal_not_interpreted_as_network(self):
        raw='execve("/tmp/guardian-test", [], []) = 0\n--- SIGURG {si_signo=SIGURG} ---\n+++ exited with 0 +++\n'
        self.assertEqual(audit.inspect_trace(raw,BINARY)["initial_execve"],1)

if __name__=="__main__":unittest.main()
