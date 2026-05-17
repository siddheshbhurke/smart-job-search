const API_BASE =
    window.location.origin;
let currentResumeText = "";


// =====================================================
// ELEMENTS
// =====================================================

const recommendBtn =
    document.getElementById(
        "recommend-btn"
    );

const refineBtn =
    document.getElementById(
        "refine-btn"
    );


// =====================================================
// RECOMMEND FLOW
// =====================================================

recommendBtn.addEventListener(
    "click",
    async () => {

        const resumeText =
            document.getElementById(
                "resume-text"
            ).value.trim();

        if (!resumeText) {

            alert(
                "Please paste resume text"
            );

            return;
        }

        currentResumeText =
            resumeText;

        try {

            recommendBtn.disabled = true;

            recommendBtn.innerText =
                "Generating...";

            const response = await fetch(
                `${API_BASE}/recommend`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        resume_text:
                            resumeText
                    })
                }
            );

            const data =
                await response.json();

            console.log(
                "RECOMMEND RESPONSE:",
                data
            );

            renderCandidate(
                data.candidate
            );

            renderJobs(
                data.ranked_jobs
            );

            showClarificationQuestion(
                data.clarifying_question
            );

        } catch (error) {

            console.error(error);

            alert(
                "Recommendation failed"
            );

        } finally {

            recommendBtn.disabled = false;

            recommendBtn.innerText =
                "Generate Recommendations";
        }
    }
);


// =====================================================
// REFINE FLOW
// =====================================================

refineBtn.addEventListener(
    "click",
    async () => {

        const feedback =
            document.getElementById(
                "user-feedback"
            ).value.trim();

        if (!feedback) {

            alert(
                "Please answer the question"
            );

            return;
        }

        try {

            refineBtn.disabled = true;

            refineBtn.innerText =
                "Refining...";

            const response = await fetch(
                `${API_BASE}/refine`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        resume_text:
                            currentResumeText,

                        user_feedback:
                            feedback
                    })
                }
            );

            const data =
                await response.json();

            console.log(
                "REFINE RESPONSE:",
                data
            );

            renderJobs(
                data.ranked_jobs
            );

        } catch (error) {

            console.error(error);

            alert(
                "Refinement failed"
            );

        } finally {

            refineBtn.disabled = false;

            refineBtn.innerText =
                "Refine Recommendations";
        }
    }
);


// =====================================================
// RENDER CANDIDATE
// =====================================================

function renderCandidate(
    candidate
) {

    const section =
        document.getElementById(
            "candidate-section"
        );

    section.classList.remove(
        "hidden"
    );

    const container =
        document.getElementById(
            "candidate-info"
        );

    let skillsHTML = "";

    if (
        candidate.skills &&
        candidate.skills.length
    ) {

        candidate.skills.forEach(
            skill => {

                skillsHTML += `
                    <span class="skill">
                        ${skill}
                    </span>
                `;
            }
        );
    }

    container.innerHTML = `

        <p>
            <strong>Name:</strong>
            ${candidate.name}
        </p>

        <p>
            <strong>Experience:</strong>
            ${candidate.experience_years} years
        </p>

        <p>
            <strong>Education:</strong>
            ${candidate.education}
        </p>

        <div style="margin-top:12px;">

            <strong>Skills:</strong>

            <div style="margin-top:8px;">
                ${skillsHTML}
            </div>

        </div>
    `;
}


// =====================================================
// RENDER JOBS
// =====================================================

function renderJobs(
    jobs
) {

    const section =
        document.getElementById(
            "results-section"
        );

    section.classList.remove(
        "hidden"
    );

    const container =
        document.getElementById(
            "results"
        );

    // CLEAR OLD RESULTS

    container.innerHTML = "";

    // RENDER NEW RESULTS

    jobs.forEach(job => {

        const card =
            document.createElement(
                "div"
            );

        card.className =
            "job-card";

        card.innerHTML = `

            <h3>
                ${job.title}
            </h3>

            <p>
                <strong>Company:</strong>
                ${job.company}
            </p>

            <p>
                <strong>Similarity Score:</strong>
                ${job.similarity_score}
            </p>

            <p>
                <strong>Explanation:</strong>
                ${job.explanation}
            </p>
        `;

        container.appendChild(
            card
        );
    });
}


// =====================================================
// SHOW QUESTION
// =====================================================

function showClarificationQuestion(
    question
) {

    const section =
        document.getElementById(
            "clarification-section"
        );

    section.classList.remove(
        "hidden"
    );

    document.getElementById(
        "clarifying-question"
    ).innerText =
        question;
}
