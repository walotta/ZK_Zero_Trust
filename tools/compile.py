from bs4 import BeautifulSoup
from enum import Enum


# Reading the data inside the xml
# file to a variable under the name 
# data
with open('example_input.xml', 'r') as f:
    data = f.read()

# Passing the stored data inside
# the beautifulsoup parser, storing
# the returned object 
Bs_data = BeautifulSoup(data, "xml")

# Finding all instances of tag 
# `unique`
policy_block = Bs_data.find_all('Policy')[0]
PolicyId = policy_block.get('PolicyId')
RuleCombiningAlgId = policy_block.get('RuleCombiningAlgId')
class RuleEffect(Enum):
    PermitOverrides = 1
    DenyOverrides = 2
    FirstApplicable = 3
    OnlyOneApplicable = 4
rule_effect = RuleCombiningAlgId.split(':')[-1]
if rule_effect == 'permit-overrides':
    rule_effect = RuleEffect.PermitOverrides
elif rule_effect == 'deny-overrides':
    rule_effect = RuleEffect.DenyOverrides
elif rule_effect == 'first-applicable':
    rule_effect = RuleEffect.FirstApplicable
elif rule_effect == 'only-one-applicable':
    rule_effect = RuleEffect.OnlyOneApplicable
else:
    raise ValueError(f'Unknown RuleCombiningAlgId: {RuleCombiningAlgId}')
Rules = policy_block.find_all('Rule')

def compile_match(id, block):
    match_type = block.get('MatchId').split(':')[-1]
    attr_value = block.find_all('AttributeValue')[0].text
    attr_field = block.find_all('AttributeDesignator')[0].get('AttributeId')
    if attr_field == 'subject:role':
        attr_field = 'inp.user_role'
    elif attr_field == 'environment:ipAddress':
        attr_field = 'inp.ip'
    else:
        raise ValueError(f'Unknown AttributeId: {attr_field}')
    if match_type == 'string-equal':
        return f'''
        let {id} = {attr_field} == "{attr_value}";
        '''
    elif match_type == 'string-regexp-match':
        return f'''
        let {id} = Regex::new(r"{attr_value}").unwrap().is_match(&{attr_field});
        '''
    else:
        raise ValueError(f'Unknown MatchId: {block.get("MatchId")}')

def compile_cond(id, cond_block):
    if cond_block.name == 'Match':
        return compile_match(id, cond_block)
    blocks = [child for child in cond_block.find_all(recursive=False)]
    assert len(blocks) != 0, 'Empty target is not supported'
    assert len(set([n.name for n in blocks])) == 1
    cond_codes = [compile_cond('{}_cond{}'.format(id,j), blocks[j]) for j in range(len(blocks))]
    code = '\n'.join(cond_codes)
    if blocks[0].name == 'AnyOf':
        code += f'''
        let {id} = { ' || '.join(['{}_cond{}'.format(id,j) for j in range(len(blocks))]) };
        '''
    elif blocks[0].name == 'AllOf':
        code += f'''
        let {id} = { ' && '.join(['{}_cond{}'.format(id,j) for j in range(len(blocks))]) };
        '''
    elif blocks[0].name == 'Match':
        code += 'let {} = {};\n'.format(id, '{}_cond0'.format(id))
        assert len(blocks) == 1, 'Match block should not have peer'
    else:
        raise ValueError(f'Unknown condition block: {blocks[0].name}')
    return code

def compile_rule(id,rule):
    eff = 'true' if rule.get('Effect') == 'Permit' else 'false'
    targets = rule.find_all('Target')
    if len(targets) == 0:
        return f'''
        let {id} = {eff};
        '''
    assert len(targets) == 1, 'Multiple targets are not supported'
    target = targets[0]
    return compile_cond(id, target)

def compile_policy(rule_list, rule_effect):
    code = '''
    use policy_core::Inputs;
    use regex::Regex;
    use risc0_zkvm::guest::env;

    fn main() {
        let inp: Inputs = env::read();
    '''
    for i in range(len(rule_list)):
        code += compile_rule('rule_res_{}'.format(i), rule_list[i])
    # result store in rule_res_0 ~ rule_res_n
    if rule_effect == RuleEffect.PermitOverrides:
        code += '''
        let result = {};
        '''.format(' || '.join([f'rule_res_{i}' for i in range(len(rule_list))]))
    elif rule_effect == RuleEffect.DenyOverrides:
        code += '''
        let result = {};
        '''.format(' && '.join([f'!rule_res_{i}' for i in range(len(rule_list))]))
    elif rule_effect == RuleEffect.FirstApplicable:
        raise NotImplementedError('FirstApplicable is not implemented')
    elif rule_effect == RuleEffect.OnlyOneApplicable:
        raise NotImplementedError('OnlyOneApplicable is not implemented')
    code += '''
        env::commit(&result);
    }
    '''
    return code

with open('main.rs', 'w') as f:
    f.write(compile_policy(Rules, rule_effect))