

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize, Default)]
#[serde(default)]
pub struct Inputs {
    pub access_subject_bogus: String,
    pub resource_resource_id: String,
    pub action_action_id: String,
}

impl Inputs {
    pub fn new(access_subject_bogus: String, resource_resource_id: String, action_action_id: String) -> Self {
        Self {
            access_subject_bogus,
            resource_resource_id,
            action_action_id,
        }
    }
}