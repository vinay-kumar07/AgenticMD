from parse import parse_lammps, parse_nist
from encode import encode_data
from RAG_TECHNIQUES.helper_functions import *
import json
import matplotlib.pyplot as plt

def retrieve_top_k(k: int):
    with open("PotentialData/nist_potentials.json", "r") as f:
        all_potentials = json.load(f)

    chunks_vector_store = encode_data(all_potentials)

    chunks_query_retriever = chunks_vector_store.as_retriever(search_kwargs={"k": k})

    score = 0
    responses = []
    for element in ["Al", "C", "Be", "Si", "Na", "K", "Ca"]:
        with open(f"Questions/generated_questions_{element}.json", "r") as f:
            questions = json.load(f)
        
        for question in questions:
            context = retrieve_context_per_question(question['question'], chunks_query_retriever)
            answer_list = []
            for ctx in context:
                ctx = ast.literal_eval(ctx)
                answer_list.append(ctx['id'])

            parity = "Incorrect"
            if len(answer_list) > 0 and question['potential'] in answer_list:
                score += 1
                parity = "Correct"

            responses.append({
                "question": question['question'],
                "expected_answer": question['potential'],
                "retrieved_answers": answer_list,
                "parity": parity
            })

    print(f"Total Score: {score} out of {len(responses)}")
    with open(f"responses_{k}.json", "w") as f:
        json.dump(responses, f, indent=4)
    
    return score/len(responses)

if __name__ == "__main__":
    scores = {}
    mrr = {}
    for k in [1, 3, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50]:
        with open(f"responses_{k}.json", "r") as f:
            responses = json.load(f)
        correct_count = 0
        rr_total = 0
        for resp in responses:
            if resp['parity'] == "Correct":
                correct_count += 1
                rank = resp['retrieved_answers'].index(resp['expected_answer']) + 1
                rr_total += 1 / rank
        scores[k] = correct_count / len(responses)
        mrr[k] = rr_total / len(responses)

    #plotting the scores
    plt.plot(list(scores.keys()), list(scores.values()), marker='o', label='Recall')
    plt.plot(list(mrr.keys()), list(mrr.values()), marker='^', label='MRR')
    plt.legend()
    plt.xlabel("k")
    plt.ylabel("Score")
    plt.savefig("RAG_evaluation.png")
    plt.close()
