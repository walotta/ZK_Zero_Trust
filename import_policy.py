import os

SOURCE_ADDR = '$HOME/xacml-to-rust/output/'
INPUT_DEFINITION = 'input_definition/'
POLICY_CODE = 'policies_code/'
TARGET_ADDR = '$HOME/risc0/examples/policy/'

policy_name = 'Policy_A01.xml.rs'
print(f'moving {policy_name}')
os.system(f'cp {SOURCE_ADDR+INPUT_DEFINITION+policy_name} {TARGET_ADDR}core/src/lib.rs')
os.system(f'cp {SOURCE_ADDR+POLICY_CODE+policy_name} {TARGET_ADDR}methods/guest/src/main.rs')
