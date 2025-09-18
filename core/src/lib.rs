

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize, Default)]
#[serde(default)]
pub struct Inputs {
    pub access_subject_subject_id: String,
}

impl Inputs {
    pub fn new(access_subject_subject_id: String) -> Self {
        Self {
            access_subject_subject_id,
        }
    }
}